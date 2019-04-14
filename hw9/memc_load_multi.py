#!/usr/bin/env python
# -*- coding: utf-8 -*-
import collections
import glob
import gzip
import itertools
import logging
import multiprocessing
import os
import sys
import threading
import time
from Queue import Queue
from functools import partial
from multiprocessing.pool import ThreadPool
from optparse import OptionParser
# brew install protobuf
# protoc  --python_out=. ./appsinstalled.proto
# pip install protobuf
import appsinstalled_pb2
# pip install python-memcached
import memcache


############### SETTINGS ###############

AppsInstalled = collections.namedtuple(
    "AppsInstalled", ["dev_type", "dev_id", "lat", "lon", "apps"]
)

RETRY = 3
BACKOFF_FACTOR = 0.1
READ_CHUNK_SIZE = 10000
UPLOAD_CHUNK_SIZE = 1000

NORMAL_ERR_RATE = 0.01
DEFAULT_PATTERN = "/data/appsinstalled/*.tsv.gz"

SENTINEL = object()

try:
    CPU_COUNT = multiprocessing.cpu_count()
except NotImplementedError:
    CPU_COUNT = 2


############### SERVICE ###############

def dot_rename(path):
    head, fn = os.path.split(path)
    # atomic in most cases
    os.rename(path, os.path.join(head, "." + fn))


def parse_appsinstalled(line):
    line_parts = line.strip().split("\t")
    if len(line_parts) < 5:
        return
    dev_type, dev_id, lat, lon, raw_apps = line_parts
    if not dev_type or not dev_id:
        return
    try:
        apps = [int(a.strip()) for a in raw_apps.split(",")]
    except ValueError:
        apps = [int(a.strip()) for a in raw_apps.split(",") if a.isidigit()]
        logging.info("Not all user apps are digits: `%s`" % line)
    try:
        lat, lon = float(lat), float(lon)
    except ValueError:
        logging.info("Invalid geo coords: `%s`" % line)
    return AppsInstalled(dev_type, dev_id, lat, lon, apps)


def get_appsinstalled_as_key_value(appsinstalled):
    key = "%s:%s" % (appsinstalled.dev_type,
                     appsinstalled.dev_id)
    ua = appsinstalled_pb2.UserApps()
    ua.lat = appsinstalled.lat
    ua.lon = appsinstalled.lon
    ua.apps.extend(appsinstalled.apps)
    packed = ua.SerializeToString()
    return key, packed


def prototest():
    sample = "idfa\t1rfw452y52g2gq4g\t55.55\t42.42\t1423,43,567,3,7,23\ngaid\t7rfw452y52g2gq4g\t55.55\t42.42\t7423,424"
    for line in sample.splitlines():
        dev_type, dev_id, lat, lon, raw_apps = line.strip().split("\t")
        apps = [int(a) for a in raw_apps.split(",") if a.isdigit()]
        lat, lon = float(lat), float(lon)
        ua = appsinstalled_pb2.UserApps()
        ua.lat = lat
        ua.lon = lon
        ua.apps.extend(apps)
        packed = ua.SerializeToString()
        unpacked = appsinstalled_pb2.UserApps()
        unpacked.ParseFromString(packed)
        assert ua == unpacked
    logging.info("Test Protobuf Done!")


class ChunkReaderGenerator(object):
    def __init__(self, gen, chunk_size=READ_CHUNK_SIZE):
        self.gen = gen
        self.chunk_size = chunk_size

    def __iter__(self):
        return self

    def __next__(self):
        chunk = list(itertools.islice(self.gen, self.chunk_size))
        if not chunk:
            raise StopIteration
        return chunk

    def next(self):
        return self.__next__()


############## Application ###############

class MemcacheUploadHandler(threading.Thread):

    def __init__(self, queue, memc_addr, dry_run=False):
        threading.Thread.__init__(self)
        self.daemon = True
        self.queue = queue
        self.dry = dry_run
        self.memc_addr = memc_addr
        self.conn = memcache.Client([memc_addr])
        self.processed = self.errors = 0

    def _set_multi(self, upload_list, retry=RETRY, backoff=BACKOFF_FACTOR):
        if self.dry:
            logging.debug("%s | %s: set %s keys" % (multiprocessing.current_process().name,
                                                    self.memc_addr, len(upload_list)))
            self.processed += len(upload_list)
            return True

        upload_dict = {k: v for k, v in upload_list}
        bad_keys = self.conn.set_multi(upload_dict)

        attempt = 1
        delay = lambda x: backoff * (2**x)

        while bad_keys and attempt <= retry:
            time.sleep(delay(attempt))
            new_upload_dict = {k: v for k, v in upload_dict.items() if k in bad_keys}
            bad_keys = self.conn.set_multi(new_upload_dict)
            attempt += 1

        if not bad_keys:
            self.processed += len(upload_dict)
            return True
        else:
            self.processed += len(upload_dict) - len(bad_keys)
            self.errors += len(bad_keys)
            return False

    def run(self):
        chunk_buff = []
        buff_size = 0
        while True:
            item = self.queue.get(block=True, timeout=None)
            if item == SENTINEL:
                self.queue.task_done()
                break

            chunk_buff.append(item)
            buff_size += 1
            self.queue.task_done()

            if buff_size < UPLOAD_CHUNK_SIZE:
                continue

            self._set_multi(chunk_buff)
            chunk_buff = []
            buff_size = 0

        self._set_multi(chunk_buff)


def process_handler(options, chunk_lines):
    device_memc = {
        "idfa": options.idfa,
        "gaid": options.gaid,
        "adid": options.adid,
        "dvid": options.dvid,
    }

    processed = errors = 0
    workers = {
        dev_type: MemcacheUploadHandler(
            Queue(),
            memc_addr,
            dry_run = options.dry
        )
        for dev_type, memc_addr in device_memc.items()
    }
    for worker in workers.values():
        worker.start()

    try:
        for line in chunk_lines:
            line = line.strip()
            if not line:
                continue

            appsinstalled = parse_appsinstalled(line)
            if not appsinstalled:
                errors += 1
                continue

            memc_addr = device_memc.get(appsinstalled.dev_type)
            if not memc_addr:
                errors += 1
                logging.error("Unknow device type: %s" % appsinstalled.dev_type)
                continue

            key, value = get_appsinstalled_as_key_value(appsinstalled)
            workers[appsinstalled.dev_type].queue.put((key, value))

    except (KeyboardInterrupt, SystemExit):
        for w in workers.values():
            w.terminate()

    for w in workers.values():
        w.queue.put(SENTINEL)

    processed += sum(w.processed for w in workers.values())
    errors += sum(w.errors for w in workers.values())

    for w in workers.values():
        w.join()

    return processed, errors


def main(options):
    pool = multiprocessing.Pool(processes=int(options.workers))
    handler = partial(process_handler, options)
    fnames = sorted(glob.iglob(options.pattern))

    try:
        for fn in fnames:
            processed = errors = 0
            logging.info('Processing %s' % fn)

            with gzip.open(fn) as fd:
                file_reader = ChunkReaderGenerator(fd)
                for proc, err in pool.imap(handler, file_reader):
                    processed += proc
                    errors += err

            if not processed:
                dot_rename(fn)
                continue

            err_rate = float(errors) / processed

            if err_rate < NORMAL_ERR_RATE:
                logging.info(
                    "Processing %s done. Acceptable error rate (%s). Successfull load" % (
                        fn, err_rate))
            else:
                logging.error(
                    "Processing %s done. High error rate (%s > %s). Failed load" % (
                        fn, err_rate, NORMAL_ERR_RATE))
            dot_rename(fn)

    except (KeyboardInterrupt, SystemExit):
        pool.terminate()

    pool.join()


if __name__ == '__main__':
    op = OptionParser()
    op.add_option("-t", "--test", action="store_true", default=False)
    op.add_option("-l", "--log", action="store", default=None)
    op.add_option("-w", "--workers", action="store", default=CPU_COUNT)
    op.add_option("--dry", action="store_true", default=False)
    op.add_option("--pattern", action="store", default=DEFAULT_PATTERN)
    op.add_option("--idfa", action="store", default="127.0.0.1:33013")
    op.add_option("--gaid", action="store", default="127.0.0.1:33014")
    op.add_option("--adid", action="store", default="127.0.0.1:33015")
    op.add_option("--dvid", action="store", default="127.0.0.1:33016")
    (opts, args) = op.parse_args()
    logging.basicConfig(filename=opts.log, level=logging.INFO if not opts.dry else logging.DEBUG,
                        format='[%(asctime)s] %(levelname).1s %(message)s', datefmt='%Y.%m.%d %H:%M:%S')
    if opts.test:
        prototest()
        sys.exit(0)

    logging.info("Memc loader started with options: %s" % opts)
    try:
        main(opts)
    except Exception, e:
        logging.exception("Unexpected error: %s" % e)
        sys.exit(1)
