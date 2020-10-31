import os
import json
import unittest

"""
Before run this test you should set WEATHER_APPID in environment variables.
"""
# OR set here:
# os.environ['WEATHER_APPID']=''

WEATHER_APPID = os.environ.get("WEATHER_APPID")
if not WEATHER_APPID:
    raise RuntimeError('Please set WEATHER_APPID in environment variables.')


from ip2w import app


class TestApi(unittest.TestCase):

    def start_response_handler(self, status, headers):
        self.code = status.split()[0]
        self.status = status
        self.headers = headers

    def get_response(self, uri):
        env = {'PATH_INFO': uri}
        response = app(env, self.start_response_handler)
        return json.loads(response[0])

    def test_broken_ip(self):
        test_list = [
            '0',
            '12.3243.34.34',
            '3.6.8,4',
            '192.168.0.0.0',
        ]
        for ip in test_list:
            data = self.get_response(ip)
            self.assertEqual(self.code, '400', 'Response code {} != 400, (ip: {})'.format(self.code, ip))
            self.assertIn('error', data)
            self.assertEqual(data['error'], 'Invalid IP address')

    def test_incorrect_uri(self):
        test_list = [
            '8.8.8.8/hello',
            '/ip/192.168.0.1',
            '/json/ip',
            'about/172.20.10.7',
            '//8.8.8.8'
        ]
        for ip in test_list:
            data = self.get_response(ip)
            self.assertEqual(self.code, '404', 'Response code {} != 404, (ip: {})'.format(self.code, ip))
            self.assertIn('error', data)
            self.assertEqual(data['error'], 'Incorrect URL')

    def test_ip_bogon(self):
        test_list = [
            '0.0.0.0',
            '192.168.0.1',
            '192.168.35.7',
            '192.168.0.0',
        ]
        for ip in test_list:
            data = self.get_response(ip)
            self.assertEqual(self.code, '400', 'Response code {} != 400, (ip: {})'.format(self.code, ip))
            self.assertIn('error', data)
            self.assertEqual(data['error'], 'IP address is a bogon')

    def test_correct_response(self):
        test_list = [
            ('8.8.8.8', 'Mountain View'),
        ]
        for ip, city in test_list:
            data = self.get_response(ip)
            self.assertEqual(self.code, '200', 'Response code {} != 200, (ip: {})'.format(self.code, ip))
            self.assertIn('city', data)
            self.assertIn('temp', data)
            self.assertIn('conditions', data)
            self.assertEqual(data['city'], city, 'Wrong work! {} != {} (ip: {})'.format(
                data['city'], city, ip))

if __name__ == '__main__':
    unittest.main()
