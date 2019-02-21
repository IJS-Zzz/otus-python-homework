#!/usr/bin/env python
# -*- coding: utf-8 -*-

import redis
import time
import unittest

import context_integration
from context import store, STORE_CONFIG
from utils import cases

"""
    BEFORE RUNNING THIS TEST YOU HAVE TO RUN REDIS SERVER

    Config the following parameters in your Environment Variable
    for correct connection with Redis server:

        REDIS_HOST – Requared
        REDIS_PORT
        REDIS_PASSWORD
"""

@unittest.skipIf(not STORE_CONFIG,
                 "Address of Redis server "
                 "doesn't set in environment variables.")
class TestRedisConnection(unittest.TestCase):
    
    def test_retry(self):
        pass

    def test_get(self):
        pass


@unittest.skipIf(not STORE_CONFIG,
                 "Address of Redis server "
                 "doesn't set in environment variables.")
class TestStorage(unittest.TestCase):
    def setUp(self):
        config = {
            'host': STORE_CONFIG['host'],
            'port': STORE_CONFIG['port'],
            'db': STORE_CONFIG['db'],
            'password': STORE_CONFIG['password'],
            'timeout': 1,
            'retry': 2,
            'backoff_factor': 0.01,
        }

        self.store = store.Storage(store.RedisConnection, config)
        self.redis = redis.Redis(host=config['host'],
                                 port=config['port'],
                                 db=config['db'],
                                 password=config['password'])

        self.prefix = '_test_storage_'
        self.created_data = set()

    def tearDown(self):
        if self.created_data:
            self.redis.delete(*self.created_data)

    def get_key(self, key):
        test_key = self.prefix + key
        self.created_data.add(test_key)
        return test_key

    @cases([
        ('key', 'value'),
        ('111', 234),
        ('name', 'Alex'),
    ])
    def test_get_method(self, key, value):
        self.redis.set(self.get_key(key), value)
        self.assertEqual(self.store.get(self.get_key(key)), str(value))

    @cases([
        ('keys', 'value, value2'),
        ('222', 880),
        ('name1', 'Alex G'),
    ])
    def test_set_method(self, key, value):
        self.store.set(self.get_key(key), value)
        self.assertEqual(self.redis.get(self.get_key(key)), str(value))

    @cases([
        ('key4', 'value4'),
        ('1111', 2346),
        ('_name', 'Tony'),
    ])
    def test_cache_get_method(self, key, value):
        self.redis.set(self.get_key(key), value)
        self.assertEqual(self.store.cache_get(self.get_key(key)), str(value))

    @cases([
        ('key99', '69'),
        ('1112', 2234),
        ('name_', 'Alex T'),
    ])
    def test_cache_set_method(self, key, value):
        self.store.cache_set(self.get_key(key), value)
        self.assertEqual(self.redis.get(self.get_key(key)), str(value))

    @cases([
        ('key_key', 'value_value'),
        ('111_111', 232344),
        ('name_name', 'Alex_Alex'),
    ])
    def test_delete_method(self, key, value):
        self.redis.set(self.get_key(key), value)
        self.store.delete(self.get_key(key))
        self.assertEqual(self.redis.get(self.get_key(key)), None)

    @cases([
        ('test_key', 'test_value', 1),
    ])
    def test_cache_set_method_with_expires(self, key, value, expires):
        # expires sets an expire flag on key name for 'expires' seconds.
        self.store.cache_set(self.get_key(key), value, expires=expires)
        self.assertEqual(
            self.redis.get(self.get_key(key)),
            str(value)
        )
        time.sleep(expires)
        self.assertEqual(
            self.redis.get(self.get_key(key)),
            None
        )


class TestRedisConnectionRetry(unittest.TestCase):
    def setUp(self):
        self.count = 0

        self.host = 'wrong_host'
        self.backoff = 0
        self.redis_connection = store.RedisConnection

    def raise_exception(self, exception):
        self.count += 1
        raise exception

    def get_count_and_reset(self):
        count = self.count
        self.count = 0
        return count

    @cases([
        (redis.exceptions.ConnectionError, 0),
        (redis.exceptions.TimeoutError, 1),
        (redis.exceptions.ConnectionError, 3),
        (redis.exceptions.TimeoutError, 5),
    ])
    def test_retry_method(self, exception, retry):
        self.assertTrue(issubclass(exception, Exception))
        conn = self.redis_connection(host=self.host,
                                     retry=retry,
                                     backoff_factor=self.backoff)
        with self.assertRaises(exception):
            conn._retry(self.raise_exception, exception)
        self.assertEqual(self.get_count_and_reset(), retry + 1)


if __name__ == "__main__":
    unittest.main()
