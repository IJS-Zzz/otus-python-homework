# -*- coding: utf-8 -*-

import functools
import json
import logging
import redis
import time


class RedisConnection(object):
    def __init__(self, host='localhost', port=6379, db=0, password=None,
                 timeout=3, retry=3, backoff_factor=0.3):
        self.retry = retry
        self.backoff_factor = backoff_factor
        self.db = redis.Redis(host=host,
                              port=port,
                              db=db,
                              password=password,
                              socket_timeout=timeout,
                              socket_connect_timeout=timeout)

    def _retry(self, func, *args, **kwargs):
        attempt = 1
        while True:
            try:
                return func(*args, **kwargs)
            except (redis.exceptions.ConnectionError,
                    redis.exceptions.TimeoutError) as e:
                if attempt > self.retry:
                    logging.error("Redis storage isn't available!")
                    raise
                logging.info("Connection problem to Redis storage. "
                             "Reconnect attempt {} of {}".format(attempt, self.retry))
                attempt += 1

                # Use Delay
                delay = self.backoff_factor * (2**attempt)
                time.sleep(delay)

    def get(self, key):
        return self._retry(self.db.get, key)

    def set(self, key, value, expires=None):
        return self._retry(self.db.set, key, value, ex=expires)

    def delete(self, key):
        return self._retry(self.db.delete, key)


class Storage(object):
    def __init__(self, store, config):
        self.db = store(**config)

    def get(self, key):
        return self.db.get(key)

    def set(self, key, value):
        return self.db.set(key, value)

    def cache_get(self, key):
        try:
            return self.db.get(key)
        except (redis.exceptions.ConnectionError,
                redis.exceptions.TimeoutError) as e:
            logging.error("Cache storage isn't available!")
            return

    def cache_set(self, key, value, expires=None):
        try:
            return self.db.set(key, value, expires)
        except (redis.exceptions.ConnectionError,
                redis.exceptions.TimeoutError) as e:
            logging.error("Cache storage isn't available!")
            logging.info("Cannot save to cache database.")

    def delete(self, key):
        return self.db.delete(key)
