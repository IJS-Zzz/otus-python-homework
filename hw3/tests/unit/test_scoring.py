#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import hashlib
import json
import redis
import time
import unittest

import context_unit
from context import scoring, store
from utils import cases, MockRedisConnection


class TestGetScore(unittest.TestCase):
    def setUp(self):
        store_config = {}
        self.store = store.Storage(MockRedisConnection, store_config)

    def get_score_from_dict(self, data):
        birthday = self.get_date_obj(data.get('birthday'))
        return scoring.get_score(self.store,
                                 phone=data.get('phone'),
                                 email=data.get('email'),
                                 birthday=birthday,
                                 gender=data.get('gender'),
                                 first_name=data.get('first_name'),
                                 last_name=data.get('last_name'))

    def gen_key_from_data(self, data):
        birthday = self.get_date_obj(data.get('birthday'))
        key_parts = [
            data.get('first_name') or "",
            data.get('last_name') or "",
            data.get('phone') or "",
            birthday.strftime("%Y%m%d") if birthday is not None else "",
        ]
        return "uid:" + hashlib.md5("".join(key_parts).encode('utf8')).hexdigest()

    def get_date_obj(self, date_str):
        return datetime.datetime.strptime(date_str, '%d.%m.%Y') if date_str else None


    @cases([
        {"phone": "79115004020", "email": "mail@mail.com"},
        {"gender": 1, "birthday": "01.01.2000", "first_name": "a", "last_name": "b"},
        {"gender": 2, "birthday": "01.01.2000"},
        {"first_name": "a", "last_name": "b"},
        {"phone": "79115004020", "email": "stupnikov@mail.ru", "gender": 1, "birthday": "01.01.2000",
         "first_name": "a", "last_name": "b"},
    ])
    def test_without_score_in_cache(self, data):
        # No requests to DB
        self.assertEqual(self.store.db.db, {})
        self.assertEqual(self.store.db.get_counter, 0)
        self.assertEqual(self.store.db.set_counter, 0)

        # First request
        self.get_score_from_dict(data)
        self.assertEqual(self.store.db.get_counter, 1)
        self.assertEqual(self.store.db.set_counter, 1)

        # Second request without heavy calculation
        # return score from cache
        self.get_score_from_dict(data)
        self.assertEqual(self.store.db.get_counter, 2)
        self.assertEqual(self.store.db.set_counter, 1)

        # Clear Cache
        self.store.db.clean()


    @cases([
        ({"phone": "79115004020", "email": "mail@mail.com"}, 10),
        ({"gender": 1, "birthday": "01.01.2000", "first_name": "a", "last_name": "b"}, 15),
        ({"gender": 0, "birthday": "01.01.2000"}, 5),
        ({"gender": 2, "birthday": "01.01.2000"}, 9),
        ({"first_name": "a", "last_name": "b"}, 13),
        ({"phone": "79115004020", "email": "stupnikov@mail.ru", "gender": 1, "birthday": "01.01.2000",
         "first_name": "a", "last_name": "b"}, 30),
    ])
    def test_score_exists_in_cache(self, data, score):
        # Create score in cache
        key = self.gen_key_from_data(data)
        self.store.cache_set(key, score)

        # No requests to DB
        self.assertEqual(self.store.db.db, {key: score})
        self.assertEqual(self.store.db.get_counter, 0)
        self.assertEqual(self.store.db.set_counter, 1)

        # First request
        result = self.get_score_from_dict(data)
        self.assertEqual(self.store.db.get_counter, 1)
        self.assertEqual(self.store.db.set_counter, 1)
        self.assertEqual(result, score)

        # Clear Cache
        self.store.db.clean()

    @cases([
        ({"phone": "79115004020"}, 1.4, 1.6),
        ({"email": "mail@mail.com"}, 1.4, 1.6),
        ({"first_name": "a", "last_name": "b"}, 0.4, 0.6),
        ({"gender": 1, "birthday": "01.01.2000"}, 1.4, 1.6),
        ({"gender": 1, "birthday": "01.01.2000", "first_name": "a", "last_name": "b"}, 1.9, 2.1),
        ({"phone": "79115004020", "email": "stupnikov@mail.ru", "gender": 1, "birthday": "01.01.2000",
         "first_name": "a", "last_name": "b"}, 4.9, 5.1),
    ])
    def test_correct_calculate_score(self, data, _min, _max):
        result = self.get_score_from_dict(data)
        self.assertTrue(_min < result < _max)


class TestGetInterests(unittest.TestCase):
    def setUp(self):
        store_config = {}
        self.store = store.Storage(MockRedisConnection, store_config)

    def gen_key_from_client_id(self, cid):
        return "i:%s" % cid

    @cases([
        0,
        123,
        321,
        9999
    ])
    def test_user_not_exist_in_storage_return_empty_list(self, client_id):
        key = self.gen_key_from_client_id(client_id)
        result = scoring.get_interests(self.store, client_id)
        self.assertEqual(result, [])

    @cases([
        (0, ['travel', 'mountain', 'Patagonia']),
        (1, ['summer', 'sea']),
        (2, ['winter', 'ski']),
        (3, ['shopping', 'Milano']),
        (4, ['golf'])
    ])
    def test_user_has_interests_in_storage(self, client_id, interests):
        key = self.gen_key_from_client_id(client_id)
        value = json.dumps(interests)
        self.store.set(key, value)
        result = scoring.get_interests(self.store, client_id)
        self.assertEqual(result, interests)


if __name__ == '__main__':
    unittest.main()
