# -*- coding: utf-8 -*-

import datetime
import hashlib
import json
import requests
import unittest

import context_add_unit_folder
from context import api
from utils import cases, gen_valid_token

# BEFORE RUNNING THIS TEST YOU HAVE TO RUN HTTP-SERVER WITH THE FOLLOWING PARAMETERS:
# - ip-address http://127.0.0.1
# - port 8080

# Note: Run server with test_config for DB


class TestIntegrationWithRunningServer(unittest.TestCase):
    def setUp(self):
        self.base_url = 'http://127.0.0.1:8080/method'
        self.headers = {'Content-Type': 'application/json'}

        self.clients = {
            0: ['travel', 'mountain', 'Patagonia'],
            1: ['summer', 'sea'],
            2: ['winter', 'ski'],
            3: ['shopping', 'Milano'],
            4: ['golf']
        }
        self.data_from_store = {}

        # Create test data in DB and save exist data from them
        self.store = api.Storage(api.RedisConnection, api.STORE_CONFIG)
        for cid, interest in self.clients.items():
            key = "i:%s" % cid
            exist_data = self.store.get(key)
            if exist_data:
                self.data_from_store[key] = exist_data
            self.store.set(key, json.dumps(interest))

    def tearDown(self):
        # Delete data from DB or set exist data
        for cid in self.clients.keys():
            key = "i:%s" % cid
            if key in self.data_from_store:
                self.store.set(key, self.data_from_store[key])
            else:
                self.store.delete(key)

    def get_response_from_http_server(self, request, url=None, headers={}):
        url = url if url else self.base_url
        request_header = self.headers.copy()
        request_header.update(headers)

        request_body = json.dumps(request, ensure_ascii=False)
        response = requests.post(url, headers=request_header, data=request_body)
        return response.json(), response.status_code

    def set_valid_auth(self, request):
        login = request.get('login', '')
        account = request.get('account', '')
        request['token'] = gen_valid_token(login, account)

    @cases([
        {"account": "horns&hoofs", "login": "h&f", "method": "online_score", "token": "", "arguments": {}},
        {"account": "horns&hoofs", "login": "h&f", "method": "online_score", "token": "sdd", "arguments": {}},
        {"account": "horns&hoofs", "login": "admin", "method": "online_score", "token": "", "arguments": {}},
    ])
    def test_bad_auth(self, request):
        data, code = self.get_response_from_http_server(request)
        # data == {'code': 403, 'error': 'Forbidden'}
        self.assertEqual(api.FORBIDDEN, code)
        self.assertIn('code', data)
        self.assertEqual(api.FORBIDDEN, data['code'])
        self.assertIn('error', data)
        self.assertEqual(api.ERRORS[api.FORBIDDEN], data['error'])

    @cases([
        {"account": "horns&hoofs", "login": "h&f", "method": "online_score"},
        {"account": "horns&hoofs", "login": "h&f", "arguments": {}},
        {"account": "horns&hoofs", "method": "online_score", "arguments": {}},
    ])
    def test_invalid_method_request(self, request):
        self.set_valid_auth(request)
        data, code = self.get_response_from_http_server(request)
        self.assertEqual(api.INVALID_REQUEST, code)
        self.assertIn('code', data)
        self.assertEqual(api.INVALID_REQUEST, data['code'])
        self.assertIn('error', data)
        self.assertTrue(len(data['error']))

    @cases([
        {},
        {"phone": "79175002040"},
        {"phone": "89175002040", "email": "stupnikov@otus.ru"},
        {"phone": "79175002040", "email": "stupnikovotus.ru"},
        {"phone": "79175002040", "email": "stupnikov@otus.ru", "gender": -1},
        {"phone": "79175002040", "email": "stupnikov@otus.ru", "gender": "1"},
        {"phone": "79175002040", "email": "stupnikov@otus.ru", "gender": 1, "birthday": "01.01.1890"},
        {"phone": "79175002040", "email": "stupnikov@otus.ru", "gender": 1, "birthday": "XXX"},
        {"phone": "79175002040", "email": "stupnikov@otus.ru", "gender": 1, "birthday": "01.01.2000", "first_name": 1},
        {"phone": "79175002040", "email": "stupnikov@otus.ru", "gender": 1, "birthday": "01.01.2000",
         "first_name": "s", "last_name": 2},
        {"phone": "79175002040", "birthday": "01.01.2000", "first_name": "s"},
        {"email": "stupnikov@otus.ru", "gender": 1, "last_name": 2},
    ])
    def test_invalid_score_request(self, arguments):
        request = {"account": "horns&hoofs", "login": "h&f", "method": "online_score", "arguments": arguments}
        self.set_valid_auth(request)
        data, code = self.get_response_from_http_server(request)
        self.assertEqual(api.INVALID_REQUEST, code, arguments)
        self.assertIn('code', data)
        self.assertEqual(api.INVALID_REQUEST, data['code'])
        self.assertIn('error', data)
        self.assertTrue(len(data['error']))

    @cases([
        {"phone": "79175002040", "email": "stupnikov@otus.ru"},
        {"phone": 79175002041, "email": "stupnikov@otus.ru"},
        {"gender": 1, "birthday": "01.01.2000", "first_name": "a", "last_name": "b"},
        {"gender": 0, "birthday": "01.01.2000"},
        {"gender": 2, "birthday": "01.01.2000"},
        {"first_name": "a", "last_name": "b"},
        {"phone": "79175002040", "email": "stupnikov@otus.ru", "gender": 1, "birthday": "01.01.2000",
         "first_name": "a", "last_name": "b"},
    ])
    def test_ok_score_request(self, arguments):
        request = {"account": "horns&hoofs", "login": "h&f", "method": "online_score", "arguments": arguments}
        self.set_valid_auth(request)
        data, code = self.get_response_from_http_server(request)
        self.assertEqual(api.OK, code)
        self.assertIn('code', data)
        self.assertEqual(api.OK, data['code'])
        self.assertIn('response', data)
        score = data['response'].get('score')
        self.assertTrue(isinstance(score, (int, float)) and score >= 0, arguments)

    def test_ok_score_admin_request(self):
        arguments = {"phone": "79175002040", "email": "stupnikov@otus.ru"}
        request = {"account": "horns&hoofs", "login": "admin", "method": "online_score", "arguments": arguments}
        self.set_valid_auth(request)
        data, code = self.get_response_from_http_server(request)
        self.assertEqual(api.OK, code)
        self.assertIn('code', data)
        self.assertEqual(api.OK, data['code'])
        self.assertIn('response', data)
        score = data['response'].get('score')
        self.assertEqual(score, 42)

    @cases([
        {},
        {"date": "20.07.2017"},
        {"client_ids": [], "date": "20.07.2017"},
        {"client_ids": {1: 2}, "date": "20.07.2017"},
        {"client_ids": ["1", "2"], "date": "20.07.2017"},
        {"client_ids": [1, 2], "date": "XXX"},
    ])
    def test_invalid_interests_request(self, arguments):
        request = {"account": "horns&hoofs", "login": "h&f", "method": "clients_interests", "arguments": arguments}
        self.set_valid_auth(request)
        data, code = self.get_response_from_http_server(request)
        self.assertEqual(api.INVALID_REQUEST, code, arguments)
        self.assertIn('code', data)
        self.assertEqual(api.INVALID_REQUEST, data['code'])
        self.assertIn('error', data)
        self.assertTrue(len(data['error']))

    @cases([
        {"client_ids": [1, 5, 10], "date": datetime.datetime.today().strftime("%d.%m.%Y")},
        {"client_ids": [0, 2], "date": "19.07.2017"},
        {"client_ids": [100]},
    ])
    def test_ok_interests_request(self, arguments):
        request = {"account": "horns&hoofs", "login": "h&f", "method": "clients_interests", "arguments": arguments}
        self.set_valid_auth(request)
        data, code = self.get_response_from_http_server(request)
        self.assertEqual(api.OK, code)
        self.assertIn('code', data)
        self.assertEqual(api.OK, data['code'])
        self.assertIn('response', data)
        response = data['response']
        self.assertEqual(len(arguments["client_ids"]), len(response))
        self.assertTrue(all(isinstance(v, list) and all(isinstance(i, basestring) for i in v)
                        for v in response.values()))
        for cid in arguments["client_ids"]:
            self.assertIn(str(cid), response)

    @cases([
        {"client_ids": [1, 2, 3], "date": datetime.datetime.today().strftime("%d.%m.%Y")},
        {"client_ids": [1, 2], "date": "19.07.2017"},
        {"client_ids": [0]},
        {"client_ids": [0, 1, 2, 3, 4]},
    ])
    def test_ok_interests_request_with_exist_client_and_interest_is_not_empty(self, arguments):
        # Check that data present in DB
        for cid in arguments['client_ids']:
            self.assertIn(cid, self.clients, "Client ID %s from client_ids doesn't exist in self.clients." % cid)

        request = {"account": "horns&hoofs", "login": "h&f", "method": "clients_interests", "arguments": arguments}
        self.set_valid_auth(request)
        data, code = self.get_response_from_http_server(request)
        self.assertEqual(api.OK, code)
        self.assertIn('code', data)
        self.assertEqual(api.OK, data['code'])
        self.assertIn('response', data)
        response = data['response']
        self.assertEqual(len(arguments["client_ids"]), len(response))
        self.assertTrue(all(v and isinstance(v, list) and all(isinstance(i, basestring) for i in v)
                        for v in response.values()))
        for cid, interest in response.items():
            self.assertEqual(interest, self.clients[int(cid)])


if __name__ == "__main__":
    unittest.main()
