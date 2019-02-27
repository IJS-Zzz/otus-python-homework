#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import json
import requests
import logging


""" Check openweathermap.org api key """
WEATHER_APPID = os.environ.get("WEATHER_APPID")
if not WEATHER_APPID:
    raise RuntimeError('Please set WEATHER_APPID in environment variables.')


""" Logging Config """
# Default write log in file
try:
    # LOGGING set '0' – Write in stdout
    not_write_log = os.environ.get('LOGGING')
    LOGGING = bool(int(not_write_log))
except (ValueError, TypeError):
    LOGGING = True

LOGGING_PATH = os.environ.get("LOGGING_PATH", "/var/log/ip2w")
LOGGING_FILE = 'ip2w-error.log'


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


class StopWorkingException(Exception):
    pass


def setup_logger(logging_file=None):
    logging.basicConfig(
        filename=logging_file,
        format='[%(asctime)s] %(levelname).1s %(message)s',
        datefmt='%Y.%m.%d %H:%M:%S',
        level=logging.INFO)


def ip4_is_valid(ip):
    """ Validate IPv4 """
    match = re.match(IP4_REGEX, ip)
    if match:
        return True


def get_ip_info(ip):
    """
    Get information about IP address from
    https://ipinfo.io/ service.
    """
    url = 'http://ipinfo.io/{ip}/json'.format(ip=ip)
    try:
        response = requests.get(url, headers={
            'Accept': 'application/json'})
    except requests.exceptions.RequestException as err:
        return {"status": err.response.status_code, "message": err.message}
    try:
        return response.json()
    except ValueError as err:
        return {"status": response.status_code, "message": err.message}


def get_weather(lat, lon, api_key):
    """
    Get information about weather
    by geographic coordinates from
    https://openweathermap.org/ service.
    """
    url = 'http://api.openweathermap.org/data/2.5/weather'
    try:
        response = requests.get(url, params={
            "lat": lat,
            "lon": lon,
            "units": "metric",
            "APPID": api_key
        })
    except requests.exceptions.RequestException as e:
        return {"status": err.response.status_code, "message": err.message}
    try:
        return response.json()
    except ValueError:
        return {"status": response.status_code, "message": err.message}


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

    """ Validate URI """
    uri = env.get("PATH_INFO", "")

    if uri.startswith('/'):
        uri = uri.replace('/','',1)
    parts_uri = uri.split('/')

    if len(parts_uri) != 1:
        return response_with_error(code=NOT_FOUND,
                                   message="Incorrect URL")
    ip = uri.split('/')[0]

    if not ip4_is_valid(ip):
        return response_with_error(message="Invalid IP address")

    """ IP Info """
    ip_info = get_ip_info(ip)
    if 'bogon' in ip_info:
        # 127.0.0.1, 0.0.0.0 and so on
        return response_with_error(message="IP address is a bogon")
    if 'status' in ip_info:
        logging.error('Request failed with status code {}. message: "{}"'.format(
            ip_info['status'],
            ip_info.get('message', '')))
        raise StopWorkingException('Problems with request (ipinfo.io)')
    try:
        lat, lon = ip_info.get('loc', '').split(',')
    except ValueError:
        logging.error("Invalid JSON-scheme (ipinfo). response: {}".format(ip_info))
        raise StopWorkingException("Incorrect response (ipinfo.io)")

    """ Weather """
    weather_data = get_weather(lat, lon, WEATHER_APPID)
    if 'status' in weather_data:
        logging.error('Request failed with status code {}. message: "{}"'.format(
            weather_data['status']),
            weather_data.get('message', ''))
        raise StopWorkingException('Problems with request (openweathermap.org)')
    try:
        response = {
            "city": weather_data['name'],
            "temp": weather_data['main']['temp'],
            "conditions": weather_data['weather'][0]['description']
        }
    except KeyError:
        logging.error("Invalid JSON-scheme (ipinfo). response: {}".format(ip_info))
        raise StopWorkingException("Incorrect response (openweathermap.org)")

    """ Response """
    status = '{} OK'.format(OK)
    response_body = json.dumps(response)
    response_headers = [
        ('Content-Type', 'text/plain'),
        ('Content-Length', str(len(response_body)))
    ]
    start_response(status, response_headers)
    return [response_body]


def application(env, start_response):
    if LOGGING:
        log_file = os.path.join(LOGGING_PATH, LOGGING_FILE)
        setup_logger(log_file)
    try:
        return application_handler(env, start_response)
    except Exception as ex:
        logging.exception(ex)

        """ Return error 500 """
        status = '{} {}'.format(INTERNAL_ERROR, ERRORS[INTERNAL_ERROR])
        response_body = json.dumps({"error": INTERNAL_ERROR_MESSAGE})
        response_headers = [("Content-type", "application/json"),
                            ('Content-Length', str(len(response_body)))]
        start_response(status, response_headers)
        return [response_body]


# shortcut wsgi application
app = application
