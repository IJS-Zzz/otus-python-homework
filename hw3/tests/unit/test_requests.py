#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import json
from datetime import datetime

import context_unit
from context import api, store
from utils import cases, MockRedisConnection

class TestBaseRequest(unittest.TestCase):
    def setUp(self):
        class SimpleRequest(api.BaseRequest):
            field_1 = api.CharField(required=True)
            field_2 = api.CharField(required=False)
            field_3 = api.CharField(required=False, nullable=True)

        self.declared_fields = ['field_1', 'field_2', 'field_3']
        self.declared_fields.sort()

        self.request = SimpleRequest

    def test_fields_exist(self):
        request = self.request()
        fields = sorted(request.fields.keys())
        self.assertEqual(fields, self.declared_fields)
        for field, field_cls in request.fields.items():
            self.assertIsInstance(field_cls, api.CharField)

    def test_empty_data(self):
        data = {}
        errors = {'field_1': 'This field is required.',
                  'field_2': "This field can't be empty."}
        request = self.request(data)
        self.assertEqual(request.errors, errors)

    def test_unexpected_fields(self):
        data = {'field_1': u'string',
                'field_2': '12345',
                'field_3': 'строка',
                'field_10': 'string',
                'field_25': '12345'}
        errors = {'field_10': "Field is unexpected",
                  'field_25': "Field is unexpected"}
        request = self.request(data)
        self.assertEqual(request.errors, errors)

    def test_correct_data(self):
        data = {'field_1': u'string',
                'field_2': '12345',
                'field_3': 'строка'}
        errors = {}
        output_data = {'field_1': u'string',
                       'field_2': u'12345',
                       'field_3': u'строка'}
        request = self.request(data)
        self.assertEqual(request.errors, errors)
        self.assertEqual(request.cleaned_data, output_data)

    def test_getattr(self):
        data = {'field_1': u'string',
                'field_2': '12345',
                'field_3': 'строка'}
        errors = {}
        output_data = {'field_1': u'string',
                       'field_2': u'12345',
                       'field_3': u'строка'}
        request = self.request(data)
        self.assertTrue(request.is_valid())
        self.assertFalse(request.errors)

        # Declared fields like class attribute
        # example: instance.field
        for key, value in output_data.items():
            self.assertEqual(getattr(request, key), value)
        with self.assertRaises(AttributeError):
            request.undeclared_field


class TestClientsInterestsRequest(unittest.TestCase):
    def setUp(self):
        self.request = api.ClientsInterestsRequest

        store_config = {}
        self.store = store.Storage(MockRedisConnection, store_config)

        # Init test data in storage
        self.clients = {
            1000: ['travel', 'mountain', 'Patagonia'],
            2001: ['summer', 'sea'],
            2002: ['winter', 'ski'],
            3000: ['shopping', 'Milano'],
            5555: ['golf']
        }
        for cid, interest in self.clients.items():
            self.store.set("i:%s" % cid, json.dumps(interest))

    def test_empty_request(self):
        data = {}
        errors = {'client_ids': 'This field is required.'}
        request = self.request(data)
        self.assertEqual(request.errors, errors)

    def test_fields_value_is_none(self):
        data = {'client_ids': None,
                'date': None}
        errors = {'client_ids': "This field can't be empty."}
        request = self.request(data)
        self.assertEqual(request.errors, errors)

    @cases([
        [1000],
        [1000, 2001],
        [5555, 3000],
        [2001, 2002, 3000],
        [1000, 2001, 2002, 3000, 5555]
    ])
    def test_get_answer(self, case):
        data = {'client_ids': case,
                'date': None}
        context = {}
        is_admin = False

        request = self.request(data)
        self.assertTrue(request.is_valid())

        result = request.get_answer(self.store, context, is_admin)
        self.assertEqual(context['nclients'], len(case))
        self.assertIsInstance(result, dict)
        for cid in case:
            self.assertEqual(result[cid], self.clients[cid])


class TestOnlineScoreRequest(unittest.TestCase):
    def setUp(self):
        self.request = api.OnlineScoreRequest

        store_config = {}
        self.store = store.Storage(MockRedisConnection, store_config)

    def test_empty_request(self):
        data = {}
        errors = {'invalid_pairs': 'Request must have at least one pair '
                                   'with non-empty values of: '
                                   '(phone, email), (first_name, last_name), '
                                   '(gender, birthday)'}
        request = self.request(data)
        self.assertEqual(request.errors, errors)

    def test_fields_value_is_none(self):
        data = {'first_name': None,
                'last_name': None,
                'email': None,
                'phone': None,
                'birthday': None,
                'gender': None}
        errors = {'invalid_pairs': 'Request must have at least one pair '
                                   'with non-empty values of: '
                                   '(phone, email), (first_name, last_name), '
                                   '(gender, birthday)'}
        request = self.request(data)
        self.assertEqual(request.errors, errors)

    @cases([
        {'first_name': 'Tom', 'last_name': 'Fast'},
        {'email': 'mail@mail.com', 'phone': '79998887766'},
        {'birthday': '10.10.2000', 'gender': 1},
        {'first_name': 'Tonny', 'last_name': 'West',
         'email': 'tonny@mail.com', 'phone': '79990000000'},
        {'first_name': 'Ann', 'last_name': 'Loo',
         'email': 'loooooo@mail.com', 'phone': '76660006600',
         'birthday': '30.05.1990', 'gender': 2},
    ])
    def test_get_answer_is_admin(self, data):
        context = {}
        is_admin = True
        response = {'score': 42}

        request = self.request(data)
        self.assertTrue(request.is_valid())
        result = request.get_answer(self.store, context, is_admin)
        self.assertEqual(result, response)

    @cases([
        {'first_name': 'Tom', 'last_name': 'Fast'},
        {'email': 'mail@mail.com', 'phone': '79998887766'},
        {'birthday': '10.10.2000', 'gender': 1},
        {'first_name': 'Tonny', 'last_name': 'West',
         'email': 'tonny@mail.com', 'phone': '79990000000'},
        {'first_name': 'Ann', 'last_name': 'Loo', 
         'email': 'loooooo@mail.com', 'phone': '76660006600',
         'birthday': '30.05.1990', 'gender': 2},
    ])
    def test_get_answer_add_info_to_context(self, data):
        context = {}
        is_admin = False
        has = sorted(data.keys())

        request = self.request(data)
        self.assertTrue(request.is_valid())
        request.get_answer(self.store, context, is_admin)
        self.assertEqual(sorted(context["has"]), has)


class TestMethodRequest(unittest.TestCase):
    def setUp(self):
        self.request = api.MethodRequest

    def test_empty_request(self):
        data = {}
        errors = {'login': 'This field is required.',
                  'token': 'This field is required.',
                  'method': 'This field is required.',
                  'arguments': 'This field is required.'}
        request = self.request(data)
        self.assertEqual(request.errors, errors)

    def test_fields_value_is_none(self):
        data = {'account': None,
                'login': None,
                'token': None,
                'method': None,
                'arguments': None}
        errors = {'method': "This field can't be empty."}
        request = self.request(data)
        self.assertEqual(request.errors, errors)

    def test_is_admin(self):
        data = {'account': None,
                'login': api.ADMIN_LOGIN,
                'token': None,
                'method': 'method',
                'arguments': None}
        request = self.request(data)

        self.assertTrue(request.is_valid())
        self.assertTrue(request.is_admin)

    @cases([
        'valera',
        'mars99',
        'koffol69',
        '123',
        'админ'
    ])
    def test_is_admin(self, login):
        data = {'account': None,
                'login': login,
                'token': None,
                'method': 'method',
                'arguments': None}
        request = self.request(data)
        
        self.assertTrue(request.is_valid())
        self.assertFalse(request.is_admin)


if __name__ == "__main__":
    unittest.main()