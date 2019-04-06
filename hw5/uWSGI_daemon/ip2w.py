#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import os
import re
import json
import requests
import logging
import time


""" Check openweathermap.org api key """
WEATHER_APPID = os.environ.get("WEATHER_APPID")
if not WEATHER_APPID:
    raise RuntimeError('Please set WEATHER_APPID in environment variables.')


############### SETTINGS ###############

LOGGING_PATH = '/var/log/ip2w'
LOGGING_FILE = 'ip2w-error.log'
LOGGING_LEVEL = logging.INFO

RETRY = 3
BACKOFF_FACTOR = 0.3


""" HTTP Codes """
OK = 200
BAD_REQUEST = 400
NOT_FOUND = 404
INTERNAL_ERROR = 500
ERRORS = {
    BAD_REQUEST: "Bad Request",
    NOT_FOUND: "Not Found",
    INTERNAL_ERROR: "Internal Server Error",
}

INTERNAL_ERROR_MESSAGE = 'Oops! Something went wrong, sorry. We fix it at soon.'

""" Regular expression for check IPv4 """
IP4_REGEX = re.compile(r"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$")


############### SERVICE ###############

def parse_args():
    parser = argparse.ArgumentParser(description="ip2w server")
    # Logging
    parser.add_argument(
        '--log',
        dest='logging',
        action='store_true',
        help="Enable write logging. (flag)")
    # Logging path
    parser.add_argument(
        '--logpath',
        dest='log_path',
        action='store',
        help="Path to logging directory.")
    
    return parser.parse_args()

def setup_logger(logging_file=None, level=logging.INFO):
    logging.basicConfig(
        filename=logging_file,
        format='[%(asctime)s] %(levelname).1s %(message)s',
        datefmt='%Y.%m.%d %H:%M:%S',
        level=level)


############### Application ###############

class StopWorkingException(Exception):
    pass


class ResponseWithErrorException(Exception):
    def __init__(self,
                 code=BAD_REQUEST,
                 message=ERRORS[BAD_REQUEST]):
        super(ResponseWithErrorException, self).__init__()
        self.code = code
        self.message = message


def requests_connect_retry(func, uri, *args, **kwargs):
    attempt = 1
    while True:
        try:
            return func(uri, *args, **kwargs)
        except requests.exceptions.RequestException as e:
            if attempt > RETRY:
                logging.error("Connection to {} failed".format(uri))
                raise
            logging.info(("Connection problem to API service.\nURI: {}\n"
                          "Reconnect attempt {} of {}").format(uri, attempt, RETRY))
            attempt += 1

            # Use Delay
            delay = BACKOFF_FACTOR * (2**attempt)
            time.sleep(delay)


def get_ip_info(ip):
    """
    Get information about IP address from
    https://ipinfo.io/ service.
    """
    url = 'http://ipinfo.io/{ip}/json'.format(ip=ip)
    try:
        response = requests_connect_retry(
            requests.get,
            url,
            headers={
                'Accept': 'application/json'
            }
        )
    except requests.exceptions.RequestException as err:
        raise StopWorkingException(
            'Problems with request from {} (ipinfo.io).\nError message: {}'.format(
                url, err.message))
    try:
        return response.json()
    except ValueError as err:
        msg = 'Wrong json response from {} (ipinfo.io).\nError message: {}'.format(
            url, err.message)
        logging.error(msg)
        raise StopWorkingException(msg)


def get_weather(lat, lon, api_key):
    """
    Get information about weather
    by geographic coordinates from
    https://openweathermap.org/ service.
    """
    url = 'http://api.openweathermap.org/data/2.5/weather'
    try:
        response = requests_connect_retry(
            requests.get,
            url,
            params={
                "lat": lat,
                "lon": lon,
                "units": "metric",
                "APPID": api_key
            }
        )
    except requests.exceptions.RequestException as err:
        raise StopWorkingException(
            'Problems with request from {} (openweathermap.org).\nError message: {}'.format(
            url, err.message))
    try:
        return response.json()
    except ValueError as err:
        msg = 'Wrong json response from {} (openweathermap.org).\nError message: {}'.format(
            url, err.message)
        logging.error(msg)
        raise StopWorkingException(msg)


def ip4_is_valid(ip):
    """ Validate IPv4 """
    match = re.match(IP4_REGEX, ip)
    if match:
        return True


def validate_uri_and_get_ip(uri):
    """ Validate URI """
    if uri is None:
        uri = ""

    if uri.startswith('/'):
        uri = uri.replace('/', '', 1)
    parts_uri = uri.split('/')

    if len(parts_uri) != 1:
        raise ResponseWithErrorException(code=NOT_FOUND,
                                         message="Incorrect URL")
    ip = parts_uri[0]

    if not ip4_is_valid(ip):
        raise ResponseWithErrorException(message="Invalid IP address")

    return ip


def get_ip_geolocation(ip):
    """ IP Info """
    ip_info = get_ip_info(ip)

    if 'bogon' in ip_info:
        # 127.0.0.1, 0.0.0.0 and so on
        raise ResponseWithErrorException(message="IP address is a bogon")
    try:
        lat, lon = ip_info.get('loc', '').split(',')
    except ValueError:
        logging.error("Invalid JSON-scheme (ipinfo). response: {}".format(ip_info))
        raise StopWorkingException("Incorrect response (ipinfo.io)")

    return lat, lon


def get_weather_response(lat, lon):
    """ Weather """
    weather_data = get_weather(lat, lon, WEATHER_APPID)
    try:
        response = {
            "city": weather_data['name'],
            "temp": weather_data['main']['temp'],
            "conditions": weather_data['weather'][0]['description']
        }
    except KeyError:
        logging.error("Invalid JSON-scheme (ipinfo). response: {}".format(ip_info))
        raise StopWorkingException("Incorrect response (openweathermap.org)")

    return response


def do_response(start_response, code, response):
    """ Response """
    if code == OK:
        status = '{} OK'.format(OK)
    else:
        if code not in ERRORS:
            logging.error('Unexpected response code - {}'.format(code))
        status = '{} {}'.format(code, ERRORS[code])

    response_body = json.dumps(response)
    response_headers = [
        ('Content-Type', 'application/json'),
        ('Content-Length', str(len(response_body)))
    ]
    start_response(status, response_headers)
    return [response_body]


def application_handler(env, start_response):
    """
    WSGI request handler
    """
    def response_with_error(code=BAD_REQUEST, message=''):
        """
        Response error handler
        """
        if code not in ERRORS:
            logging.error('Unexpected response code - {}'.format(code))

        status = '{} {}'.format(code, ERRORS[code])
        response_body = json.dumps({"error": message})
        response_headers = [
            ('Content-Type', 'application/json'),
            ('Content-Length', str(len(response_body)))
        ]
        start_response(status, response_headers)
        return [response_body]

    try:
        uri = env.get("PATH_INFO", "")
        ip = validate_uri_and_get_ip(uri)
        lat, lon = get_ip_geolocation(ip)
        response = get_weather_response(lat, lon)
    except ResponseWithErrorException as e:
        fail_response = {"error": e.message}
        return do_response(start_response, e.code, fail_response)

    return do_response(start_response, OK, response)


def application(env, start_response):
    args = parse_args()
    if args.logging:
        log_path = args.log_path if args.log_path else LOGGING_PATH
        log_file = os.path.join(log_path, LOGGING_FILE)
        setup_logger(log_file, level=LOGGING_LEVEL)
    try:
        return application_handler(env, start_response)
    except Exception as ex:
        logging.exception(ex)

        """ Return error 500 """
        fail_response = {"error": INTERNAL_ERROR_MESSAGE}
        return do_response(start_response, INTERNAL_ERROR, fail_response)


# shortcut wsgi application
app = application
