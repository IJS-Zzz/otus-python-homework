#!/usr/bin/env python
# -*- coding: utf-8 -*-

import redis
import socket
import sys
import time
import unittest


import context_integration
from context import store, STORE_CONFIG
from utils import cases, connect_failer

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


@unittest.skipIf(not STORE_CONFIG,
                 "Address of Redis server "
                 "doesn't set in environment variables.")
class TestRedisConnectionRetry(unittest.TestCase):
    """
        Test case:
        Сheck of reconnection functions at disconnection.
    """

    def setUp(self):
        self.config = config = {
            'host': STORE_CONFIG['host'],
            'port': STORE_CONFIG['port'],
            'db': STORE_CONFIG['db'],
            'password': STORE_CONFIG['password'],
            'timeout': 1,
            'retry': 2,
            'backoff_factor': 0.01,
        }

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
        ('key', 'value', 0),
        ('key2', '234', 1),
        ('name', 'Alex', 4),
    ])
    def test_retry_with_get_method(self, key, value, retry):
        config = self.config
        config['retry'] = retry

        # Set value in DB
        self.redis.set(self.get_key(key), value)

        storage = store.Storage(store.RedisConnection, config)
        self.assertIsInstance(storage.db.db, redis.Redis)
        storage.db.db.get = connect_failer(retry)(storage.db.db.get)

        # Get value from DB with N times failed connection
        self.assertEqual(storage.get(self.get_key(key)), value)
        self.assertEqual(storage.db.db.get.calls, retry)

    @cases([
        ('name', 'Garry', 1),
        ('age', '23', 2),
        ('car', 'Lada', 5),
    ])
    def test_retry_with_set_method(self, key, value, retry):
        config = self.config
        config['retry'] = retry

        storage = store.Storage(store.RedisConnection, config)
        self.assertIsInstance(storage.db.db, redis.Redis)
        storage.db.db.set = connect_failer(retry)(storage.db.db.set)

        # Set value in DB with N times failed connection
        self.assertTrue(storage.set(self.get_key(key), value))
        self.assertEqual(storage.db.db.set.calls, retry)

        # Check value in DB
        self.assertEqual(self.redis.get(self.get_key(key)), value)

    @cases([
        ('name', 'Lora', 1),
        ('age', '97', 2),
        ('car', 'Volvo', 5),
    ])
    def test_retry_fail(self, key, value, retry):
        """
            _retry methor of RedisConnection try to connect N-1 times
            connect_failer drop connect N times
        """
        config = self.config
        config['retry'] = retry - 1

        storage = store.Storage(store.RedisConnection, config)
        self.assertIsInstance(storage.db.db, redis.Redis)
        storage.db.db.set = connect_failer(retry)(storage.db.db.set)

        self.assertTrue(storage.db.db.ping())
        with self.assertRaises(redis.exceptions.ConnectionError):
            storage.set(key, value)
        self.assertEqual(storage.db.db.set.calls, retry)


if __name__ == "__main__":
    unittest.main()
