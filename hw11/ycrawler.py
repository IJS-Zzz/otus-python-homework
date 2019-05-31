#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import aiohttp
import argparse
import asyncio
import logging
import os
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from tempfile import NamedTemporaryFile
from urllib.parse import urlparse


############### SETTINGS ###############

CONTENT_FOLDER = './news'
POLL_PERIOD = 30  # Seconds

Y_ROOT_URL = "https://news.ycombinator.com/"
Y_POST_URL = "https://news.ycombinator.com/item?id={}"

POST_FILE_NAME = "post_{}.html"
COMMENT_FILE_NAME = "comment_{}.html"

LOG_FILE_PATH = './'
LOG_FILENAME = "ycrawler.log"

WORKERS = 30
SENTINEL = "STOP"
THREAD_POOL_EX_SIZE = WORKERS * 10
REQUEST_TIMEOUT = 60
SAVE_CHUNK_SIZE = 1024

MAX_RETRIES = 3
BACKOFF_FACTOR = 0.3


############### SERVICE ###############

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=("Async crawler for download news "
                     "from http://news.ycombinator.com"))
    # Content folder
    parser.add_argument(
        "--store_dir",
        type=str,
        default=CONTENT_FOLDER,
        action="store",
        help="Path to folder for save content.")
    # Poll period
    parser.add_argument(
        "--period",
        type=int,
        default=POLL_PERIOD,
        action="store",
        help="Number of seconds between poll.")

    # Logging
    parser.add_argument(
        "--log",
        action="store_true",
        help="Enable logging.")
    # Logging file path
    parser.add_argument(
        "--log_path",
        type=str,
        default=LOG_FILE_PATH,
        action="store",
        help="Path to logging file.")
    # Verbose logging
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose logging.")
    return parser.parse_args()


def setup_logger(log: bool = False,
                 log_path: str = None,
                 verbose: bool = False):
    logging.basicConfig(
        filename=os.path.join(log_path, LOG_FILENAME) if log else None,
        format='[%(asctime)s] %(levelname).1s %(message)s',
        datefmt='%Y.%m.%d %H:%M:%S',
        level=logging.DEBUG if verbose else logging.INFO)


############## Application ###############

############## Fetcher ###############

class Fetcher:
    """
    Class for async fetching data from URLs
    """

    def __init__(self,
                 session: aiohttp.ClientSession,
                 loop: asyncio.BaseEventLoop=None,
                 executor: ThreadPoolExecutor=None,
                 retry: int=MAX_RETRIES,
                 backoff_factor: float=BACKOFF_FACTOR,
                 save_chunk_size: int=SAVE_CHUNK_SIZE):
        self.session = session
        self.loop = loop or asyncio.get_event_loop()
        self.executor = executor
        self.retry = retry
        self.backoff_factor = backoff_factor
        self.chunk_size = save_chunk_size

    async def _fetch(self, url: str, save_in_file: str='') -> str:
        """
        Fetch an URL using aiohttp.
        """
        attempt = 1
        while True:
            try:
                async with self.session.get(url) as response:
                    if save_in_file:
                        return await self._save_response_in_file(response, save_in_file)
                    return await response.text()

            except (aiohttp.ClientError, asyncio.TimeoutError) as ex:
                if attempt > self.retry:
                    logging.error("Can't fetch url {}. {}: {}".format(
                        url, type(ex).__name__, ex.args))
                    raise

                delay = self.backoff_factor * (2**attempt)
                logging.debug(
                    "Request failed, url {}. {}: {}. Sleep {} sec and retry".format(
                        url, type(ex).__name__, ex.args, delay))
                await asyncio.sleep(delay)
                attempt += 1

    async def _save_response_in_file(self, response, path):
        """
        Handler for save response as bytes in file.
        """
        save_dir = os.path.dirname(path)
        with NamedTemporaryFile(mode='w+b', dir=save_dir) as temp_file:
            while True:
                chunk = await response.content.read(self.chunk_size)
                if not chunk:
                    break
                await self.loop.run_in_executor(self.executor, temp_file.write, chunk)
            temp_file.flush()

            # save output file after completion of write temp file
            if os.path.exists(path):
                os.remove(path)
                logging.debug("File was rewritten {}".format(path))
            os.link(temp_file.name, path)
        logging.debug("Download {} complete".format(path))
        return path

    async def fetch(self, url: str) -> str:
        """
        Fetch an URL.

        return: html page as string
        """
        return await self._fetch(url)

    async def fetch_and_save(self, url: str, path: str) -> str:
        """
        Fetch an URL
        and save response in file.

        return: path to saved file
        """
        return await self._fetch(url, save_in_file=path)


############## Posts Download Worker ###############

async def posts_download_worker(w_id: int,
                                fetcher: Fetcher,
                                queue: asyncio.Queue,
                                store_dir: str):
    """
    Function for parse  and download new post.
    """
    while True:
        task = await queue.get()
        if task == SENTINEL:
            queue.task_done()
            logging.warning("Worker {} got SENTINEL - exit.".format(w_id))
            return

        post_id, url = task
        comments_links = await get_links_from_comments(fetcher, post_id)

        logging.debug("Worker {} - found {} links in post {}".format(
            w_id, (1 + len(comments_links)), post_id
        ))

        post_dir = os.path.join(store_dir, str(post_id))
        os.makedirs(post_dir, exist_ok=True)

        tasks = [
            post_download_handler(
                fetcher, _url, post_dir, post_id, comment_id=i)
            for i, _url in enumerate(comments_links)
        ]
        tasks.insert(0, post_download_handler(fetcher, url, post_dir, post_id))

        results = await asyncio.gather(*tasks)
        post_saved = results[:1]
        comment_saved = sum(results[1:])
        if post_saved:
            logging.info(
                "Post {} was saved with {} comments".format(post_id, comment_saved))
        else:
            logging.warning("Post {} wasn't saved".format(post_id))
        queue.task_done()


async def get_links_from_comments(fetcher: Fetcher, post_id: int) -> list:
    """
    Fetch comments page and parse links from comments.
    """
    url = Y_POST_URL.format(post_id)
    links = set()
    try:
        html = await fetcher.fetch(url)
    except (aiohttp.ClientError, asyncio.TimeoutError):
        logging.warning("No data was received from the url {}".format(url))
        return list()

    soup = BeautifulSoup(html, "html5lib")
    for link in soup.select(".comment a[rel=nofollow]"):
        _url = link.attrs["href"]
        parsed_url = urlparse(_url)
        if parsed_url.scheme and parsed_url.netloc:
            links.add(_url)

    return list(links)


async def post_download_handler(fetcher: Fetcher, url: str, path: str,
                                post_id: int, comment_id: int=None) -> bool:
    """
    Download the data from the url and save it to a file.

    return: download status(bool)
    """
    fname = get_file_name(post_id, comment_id)
    file_path = os.path.join(path, fname)
    result_file = ''
    try:
        result_file = await fetcher.fetch_and_save(url, file_path)
    except (aiohttp.ClientError, asyncio.TimeoutError):
        pass

    if result_file:
        return True
    logging.debug("No data was received from the url {}".format(url))
    return False


def get_file_name(post_id: int, comment_id: int=None) -> str:
    """
    Generate filename by post id and comment id.
    """
    if comment_id != None:
        return 'comment_{}.html'.format(comment_id)
    return 'post_{}.html'.format(post_id)


############## New Posts Watcher ###############

async def new_posts_watcher(fetcher: Fetcher,
                            queue: asyncio.Queue,
                            store_dir: str,
                            sleep_time: int,
                            num_workers: int):
    """
    Function for search news post on main page
    of  https://news.ycombinator.com/ 
    and send tasks of downloads to workers.
    """
    logging.info("Ycrawler started.")

    iteration = 1
    while True:
        try:
            new_posts = await get_new_posts(fetcher, store_dir)
            for post_id, post_url in new_posts.items():
                await queue.put((post_id, post_url))
        except Exception as ex:
            logging.exception(ex)
            for _ in range(num_workers):
                await queue.put(SENTINEL)
            return

        await queue.join()

        logging.info("Waiting for {} sec...".format(sleep_time))
        await asyncio.sleep(sleep_time)
        iteration += 1

        logging.info("Run new search iteration ({})".format(iteration))


async def get_new_posts(fetcher: Fetcher, store_dir: str) -> dict:
    """
    Function for searching news posts.
    """
    try:
        page = await fetcher.fetch(Y_ROOT_URL)
    except (aiohttp.ClientError, asyncio.TimeoutError):
        logging.info("{} is not available now".format(Y_ROOT_URL))
        return dict()

    posts = get_posts_from_main_page(page)
    ready_post_ids = get_processed_posts(store_dir)

    not_ready_posts = {}
    for p_id, p_url in posts.items():
        if p_id not in ready_post_ids:
            not_ready_posts[p_id] = p_url
        else:
            logging.debug("Post {} already parsed".format(p_id))

    return not_ready_posts


def get_processed_posts(store_dir: str) -> list:
    """
    Search in store_dir already downloaded posts
    """
    post_ids = list()
    if not os.path.isdir(store_dir):
        return post_ids

    for subdir_name in os.listdir(store_dir):
        if os.path.isdir(os.path.join(store_dir, subdir_name)):
            try:
                post_id = int(subdir_name)
            except ValueError:
                msg = "Wrong subdir name (should be number): {}"
                logging.debug(msg.format(subdir_name))
                continue

            path_to_file = os.path.join(
                store_dir,
                subdir_name,
                POST_FILE_NAME.format(post_id))

            if os.path.isfile(path_to_file):
                post_ids.append(post_id)

    return post_ids


def get_posts_from_main_page(page: str) -> dict:
    """
    Parse ids and links of news posts from html-page.
    """
    posts = {}

    soup = BeautifulSoup(page, "html5lib")
    trs = soup.select("table.itemlist tr.athing")
    for ind, tr in enumerate(trs):
        p_id, p_url = '', ''
        try:
            p_id = int(tr.attrs["id"])
            p_url = tr.select_one("td.title a.storylink").attrs["href"]
            posts[p_id] = p_url
        except (KeyError, ValueError):
            log.error("Error on {} post (id: {}, url: {})".format(
                ind, p_id, p_url
            ))

    return posts


############## Main ###############

async def main(args: argparse.Namespace):
    queue = asyncio.Queue()
    num_workers = WORKERS

    async with aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(ssl=False),
        timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
    ) as session:
        with ThreadPoolExecutor(max_workers=THREAD_POOL_EX_SIZE) as executor:
            fetcher = Fetcher(session=session, executor=executor)
            workers = [
                posts_download_worker(w_id, fetcher, queue, args.store_dir)
                for w_id in range(num_workers)
            ]
            workers.append(new_posts_watcher(
                fetcher, queue, args.store_dir, args.period, num_workers))
            await asyncio.gather(*workers)


if __name__ == "__main__":
    args = parse_args()
    setup_logger(args.log, args.log_path, args.verbose)
    try:
        asyncio.run(main(args))
    except KeyboardInterrupt:
        logging.info("Termination…")
    except Exception as ex:
        logging.exception(ex)
