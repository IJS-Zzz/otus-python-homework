#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import aiohttp
import argparse
import asyncio
import logging
import os
from bs4 import BeautifulSoup
from logging.handlers import RotatingFileHandler
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

    def __init__(self, session,
                 retry=MAX_RETRIES,
                 backoff_factor=BACKOFF_FACTOR,
                 save_chunk_size=1024):
        self.session = session
        self.retry = retry
        self.backoff_factor = BACKOFF_FACTOR
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

            except aiohttp.ClientError as ex:
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
                temp_file.write(chunk)
            temp_file.flush()

            # save output file after completion of write temp file
            if os.path.exists(path):
                os.remove(path)
                logging.debug("File was rewritten {}".format(path))
            os.link(temp_file.name, path)
        return path

    async def fetch(self, url: str) -> str:
        """
        Fetch an URL.

        return: html page as string
        """
        return await self._fetch(url)

    async def fetch_and_save_in_file(self, url: str, path: str) -> str:
        """
        Fetch an URL
        and save response in file.

        return: path to saved file
        """
        return await self._fetch(url, save_in_file=path)


class PostsHandler:

    def __init__(self, lock, store_dir):
        self.lock = lock
        self.store_dir = store_dir
        self._store_dir_created = False

        self.post_saved = 0
        self.comment_saved = 0
        self.ready_posts = set()
        self.scan_ready_posts()

    async def reset_counters(self):
        async with self.lock:
            self.post_saved = 0
            self.comment_saved = 0

    def create_store_dir(self, post_folder: str=None):
        """
        Handler for create directory.
        """
        if not self._store_dir_created:
            os.makedirs(self.store_dir, exist_ok=True)
            self._store_dir_created = True
        if post_folder:
            os.makedirs(os.path.join(self.store_dir,
                                     post_folder), exist_ok=True)

    def scan_ready_posts(self):
        """
        Search already downloaded news posts in content directory.
        """
        self.create_store_dir()

        post_ids = set()
        for subdir_name in os.listdir(self.store_dir):
            if os.path.isdir(os.path.join(self.store_dir, subdir_name)):
                try:
                    post_id = int(subdir_name)
                except ValueError:
                    msg = "Wrong subdir name (should be number): {}"
                    logging.debug(msg.format(subdir_name))
                    continue

                path_to_file = os.path.join(
                    self.store_dir,
                    subdir_name,
                    POST_FILE_NAME.format(post_id))

                if os.path.isfile(path_to_file):
                    post_ids.add(post_id)

        self.ready_posts.update(post_ids)

    def get_file_name(self, post_id: int, comment_id: int=None):
        """
        Generate filename by id.
        """
        base = os.path.join(self.store_dir, str(post_id))
        if comment_id != None:
            return os.path.join(base, 'comment_{}.html'.format(str(comment_id)))
        return os.path.join(base, 'post_{}.html'.format(str(post_id)))

    async def download_post(self,
                            fetcher: Fetcher,
                            post_id: int,
                            link: str):
        post_folder = str(post_id)
        self.create_store_dir(post_folder)
        filename = self.get_file_name(post_id)
        try:
            if os.path.exists(filename):
                os.rename(filename, filename + '.dump')
            await fetcher.fetch_and_save_in_file(link, filename)
            self.post_saved += 1
            self.ready_posts.add(post_id)
        except aiohttp.ClientError:
            pass

    async def download_comment(self,
                               fetcher: Fetcher,
                               post_id: int,
                               link: str,
                               comment_id: int):
        post_folder = str(post_id)
        self.create_store_dir(post_folder)
        filename = self.get_file_name(post_id, comment_id)
        try:
            await fetcher.fetch_and_save_in_file(link, filename)
            self.comment_saved += 1
        except aiohttp.ClientError:
            pass


############## Posts Download Worker ###############

async def posts_download_worker(w_id: int,
                                fetcher: Fetcher,
                                queue: asyncio.Queue,
                                posts_handler: PostsHandler):
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

        tasks = [
            posts_handler.download_comment(fetcher, post_id, link, i)
            for i, link in enumerate(comments_links)
        ]
        tasks.insert(0, posts_handler.download_post(fetcher, post_id, url))

        await asyncio.gather(*tasks)
        queue.task_done()


async def get_links_from_comments(fetcher: Fetcher, post_id: int) -> list:
    """
    Fetch comments page and parse links from comments.
    """
    url = Y_POST_URL.format(post_id)
    links = set()
    try:
        html = await fetcher.fetch(url)

        soup = BeautifulSoup(html, "html5lib")
        for link in soup.select(".comment a[rel=nofollow]"):
            _url = link.attrs["href"]
            parsed_url = urlparse(_url)
            if parsed_url.scheme and parsed_url.netloc:
                links.add(_url)
    except aiohttp.ClientError:
        pass
    finally:
        return list(links)


############## New Posts Watcher ###############

async def new_posts_watcher(fetcher: Fetcher,
                            queue: asyncio.Queue,
                            posts_handler: PostsHandler,
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
            new_posts = await check_new_posts(fetcher, posts_handler)
            for post_id, post_url in new_posts.items():
                await queue.put((post_id, post_url))
        except Exception as ex:
            logging.exception(ex)
            for _ in range(num_workers):
                await queue.put(SENTINEL)
            return

        await queue.join()

        logging.info("Saved {} posts, {} links from comments".format(
            posts_handler.post_saved, posts_handler.comment_saved
        ))

        await posts_handler.reset_counters()

        logging.info("Waiting for {} sec...".format(sleep_time))
        await asyncio.sleep(sleep_time)
        iteration += 1

        logging.info("Run new search iteration ({})".format(iteration))


async def check_new_posts(fetcher: Fetcher,
                          posts_handler: PostsHandler) -> dict:
    """
    Function for get not downloaded news posts.
    """
    page = await fetcher.fetch(Y_ROOT_URL)
    posts = get_posts_from_main_page(page)
    ready_post_ids = posts_handler.ready_posts

    not_ready_posts = {}
    for p_id, p_url in posts.items():
        if p_id not in ready_post_ids:
            not_ready_posts[p_id] = p_url
        else:
            logging.debug("Post {} already parsed".format(p_id))

    return not_ready_posts


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

async def main(loop, args: argparse.Namespace):
    lock = asyncio.Lock(loop=loop)
    queue = asyncio.Queue(loop=loop)
    posts_handler = PostsHandler(lock=lock, store_dir=args.store_dir)
    num_workers = WORKERS

    async with aiohttp.ClientSession(
        loop=loop, connector=aiohttp.TCPConnector(ssl=False)
    ) as session:
        fetcher = Fetcher(session=session)
        workers = [
            posts_download_worker(w_id, fetcher, queue, posts_handler)
            for w_id in range(num_workers)
        ]
        workers.append(new_posts_watcher(
            fetcher, queue, posts_handler, args.period, num_workers))
        await asyncio.gather(*workers)


if __name__ == "__main__":
    args = parse_args()
    setup_logger(args.log, args.log_path, args.verbose)
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main(loop, args))
    except KeyboardInterrupt:
        print("Attempting graceful shutdown, press Ctrl+C again to exit…")

        # Do not show 'asyncio.CancelledError' exceptions during shutdown
        def shutdown_exception_handler(loop, context):
            if "exception" not in context \
                    or not isinstance(context["exception"], asyncio.CancelledError):
                loop.default_exception_handler(context)
        loop.set_exception_handler(shutdown_exception_handler)

        # Handle shutdown gracefully by waiting for all tasks to be cancelled
        tasks = asyncio.gather(
            *asyncio.Task.all_tasks(loop=loop), loop=loop, return_exceptions=True)
        tasks.add_done_callback(lambda t: loop.stop())
        tasks.cancel()

        # Keep the event loop running until it is either destroyed or all
        # tasks have really terminated
        while not tasks.done() and not loop.is_closed():
            loop.run_forever()
    except Exception as ex:
        logging.exception(ex)
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()
