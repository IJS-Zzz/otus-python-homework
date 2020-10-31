#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import io
import json
import logging
import mimetypes
import multiprocessing
import os
import socket
import threading
import time
import urllib
import urlparse
from multiprocessing.pool import ThreadPool


############### SETTINGS ###############

LOGGING_LEVEL = logging.INFO

CONFIG = {
    'BIND_HOST': '0.0.0.0',
    'BIND_PORT': 8080,
    'WORKERS': 2,
    'DOCUMENT_ROOT': './',
    'LOGGING_FILE': None,
}

DEFAULT_CONFIG_PATH = './config.json'

BUFFER_SIZE = 1024
WORKER_QUEUE_SIZE = 256

OK = 200
BAD_REQUEST = 400
FORBIDDEN = 403
NOT_FOUND = 404
NOT_ALLOWED = 405

RESPONSE_CODES = {
    OK: 'OK',
    BAD_REQUEST: 'Bad Request',
    NOT_FOUND: 'Not Found',
    FORBIDDEN: 'Forbidden',
    NOT_ALLOWED: 'Method Not Allowed',
}

ALLOWED_FILE_TYPES = ('.html', '.css', '.js', '.jpg',
                      '.jpeg', '.png', '.gif', '.swf')

ALLOWED_CONTENT_TYPES = (
    'text/css',
    'text/html',
    'application/javascript',
    'image/jpeg',
    'image/png',
    'image/gif',
    'text/plain',
    'application/x-shockwave-flash'
)

ALLOWED_METHODS = ('GET', 'HEAD')

SERVER_VERSION = 'OtusServer'

PROTOCOL_VERSION = 'HTTP/1.1'

LINE_SEPARATOR = '\r\n'

HTTP_HEAD_TERMINATIOR = '\r\n\r\n'

INDEX_FILE = 'index.html'


############### SERVICE ###############

def parse_args():
    parser = argparse.ArgumentParser(description=SERVER_VERSION)
    # Workers
    parser.add_argument(
        '-w',
        action='store',
        type=int,
        dest='workers',
        help="Count of used server's workers.")
    # Root directory
    parser.add_argument(
        '-r',
        action='store',
        dest='root_dir',
        help="Server's root directory.")
    # Port
    parser.add_argument(
        '--port',
        action='store',
        type=int,
        dest='port',
        help="Port is used of the server.")
    # Logging
    parser.add_argument(
        '--logfile',
        dest='logfile',
        action='store',
        help="File for save server logs.")
    # Config
    parser.add_argument(
        '--config',
        nargs='?',
        const=DEFAULT_CONFIG_PATH,
        dest='config',
        help="Config file path. Using JSON format.")

    return parser.parse_args()


def load_config(config, conf_path=None):
    if not conf_path:
        return config

    with io.open(conf_path, 'rb') as file:
        config.update(json.load(file, encoding='utf-8'))
    return config


def update_config_with_parse_args(config, parse_args):
    if args.workers:
        if args.workers > 0:
            config['WORKERS'] = args.workers
        else:
            raise RuntimeError("Worker's count is uncorrelated. Must be greater than 0")

    if args.root_dir:
        if os.path.isdir(os.path.abspath(args.root_dir)):
            config['DOCUMENT_ROOT'] = args.root_dir
        else:
            raise RuntimeError("Path '{}' doesn't exist.".format(args.root_dir))

    if args.port:
        if args.port > 0:
            config['BIND_PORT'] = args.port
        else:
            raise RuntimeError("Uncorrected port.")

    return config


def setup_logger(logging_file=None, level=logging.INFO):
    logging.basicConfig(
        filename=logging_file,
        format='[%(asctime)s] %(levelname).1s %(message)s',
        datefmt='%Y.%m.%d %H:%M:%S',
        level=level)


############### UTILITIES ###############

def get_cleaned_url_wo_query_string(url):
    print(url)
    decode_url = urllib.unquote(url)
    path = urlparse.urlparse(decode_url).path
    return os.path.normpath(path)


def file_finder(root_dir, index_file, path):
    path = os.path.join(root_dir, path[1:])
    file = None

    if os.path.isdir(path):
        path = os.path.join(path, index_file)
    if os.path.isfile(path):
        file = path
    return file


def get_file_mimetype(path):
    _, ext = os.path.splitext(path)
    return mimetypes.types_map[ext.lower()]


############### Thread HTTP Server ###############

class ThreadHTTPServer(object):
    def __init__(self, host, port, root_dir,request_handler,
                 sock_backlog=WORKER_QUEUE_SIZE, pool_size=100):
        self.sock = None
        self.sock_backlog = sock_backlog
        self.pool_size = pool_size

        self.address = (host, port)
        self.root_dir = root_dir
        self.request_handler = request_handler

        self.create_socket()

    def create_socket(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            self.sock.bind(self.address)
            self.sock.listen(self.sock_backlog)
        except socket.error as e:
            raise RuntimeError(e)

    def serve_forever(self):
        try:
            pool = ThreadPool(self.pool_size)

            while True:
                conn, addr = self.sock.accept()
                logging.debug('Connected | P: {} | PID: {}'.format(
                    multiprocessing.current_process().name, os.getpid()))
                pool.apply(self.request_handler, args=(conn, addr, self.root_dir, True))

        except (KeyboardInterrupt, SystemExit) as e:
            pass
        finally:
            self.sock.close()
            logging.debug('Stopped | P: {} | PID: {}'.format(
                    multiprocessing.current_process().name, os.getpid()))


class RequestHandler(object):
    """RequestHandler is a class for processing client requests"""
    def __init__(self, connection, client_address, root_dir, run=False):
        self.conn = connection
        self.client_address = client_address
        self.root_dir = root_dir

        self.index_file = INDEX_FILE
        self.buf_size = BUFFER_SIZE
        self.termination = HTTP_HEAD_TERMINATIOR
        self.line_separator = LINE_SEPARATOR

        self.keep_alive = False

        # service
        self.process = multiprocessing.current_process().name
        self.thread = threading.current_thread().name

        self.debug_info = ' | P: {} | T: {} | PID: {}'.format(self.process, self.thread, os.getpid())

        if run:
            self.run()

    def run(self):
        try:
            logging.debug('Request handler running' + self.debug_info)
            self.handle_request()
            while self.keep_alive:
                self.handle_request()
        finally:
            self.shutdown()

    def shutdown(self):
        self.conn.close()

    def handle_request(self):
        self.keep_alive = False

        raw_data = self.recv_data()
        request = self.parse_request(raw_data)
        raw_response = self.process_request(request)

        logging.debug('New request from {}{}\n{}'.format(self.client_address,
                                                         self.debug_info,
                                                         raw_data))
        logging.debug('Raw response to {}{}\n{}'.format(
            self.client_address,
            self.debug_info,
            '\n'.join('{}: {}'.format(k,v) for k,v in raw_response.items())
        ))

        logging.info('({addr}) "{method} {url} {version}" {code}'.format(
            addr = self.client_address[0],
            method = request['method'],
            url = request['url'],
            version = request['version'],
            code = raw_response['code']
        ))

        if raw_response['code'] != OK:
            return self.do_ERROR(raw_response)

        # Connection: Keep-Alive
        if raw_response['headers']['Connection'] == 'Keep-Alive':
            self.keep_alive = True

        method = getattr(self, 'do_' + raw_response['method'])
        return method(raw_response)

    def parse_request(self, raw_data):
        request = {
            'method': '',
            'url': '',
            'version': '',
            'headers': {}
        }
        request_lines = raw_data.split(self.line_separator)

        first_line = request_lines[0].split()
        if len(first_line) == 3:
            method, url, version = first_line
            request['method'] = method
            request['url'] = url
            request['version'] = version

        for line in request_lines[1:]:
            # Check empty line
            if not line.split():
                break
            k, v = line.split(':', 1)
            request['headers'][k.lower()] = v.strip()

        return request

    def process_request(self, request):
        response = {
            'code': BAD_REQUEST,
            'method': None,
            'url': None,
            'file': None,
            'headers': {
                'Date': time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime()),
                'Server': SERVER_VERSION,
                'Content-Type': 'text/html',
                'Content-Length': '0',
                'Connection': 'close',
            }
        }
        if not all((request['method'], request['url'], request['version'])):
            return response

        if request['method'] not in ALLOWED_METHODS:
            response['code'] = NOT_ALLOWED
            return response

        url = get_cleaned_url_wo_query_string(request['url'])

        # Check file exists (if url is folder check index file in this folder)
        file = file_finder(self.root_dir, self.index_file, url)
        if not file:
            response['code'] = NOT_FOUND
            return response

        # Check file is readable
        if not os.access(file, os.R_OK):
            response['code'] = FORBIDDEN
            return response

        file_size = os.path.getsize(file)

        mimetype = get_file_mimetype(file)
        if mimetype not in ALLOWED_CONTENT_TYPES:
            response['code'] = FORBIDDEN
            return response

        connection = request['headers'].get('connection')
        if connection and connection.lower() == 'keep-alive':
            response['headers']['Connection'] = 'Keep-Alive'

        response.update({
            'code': OK,
            'method': request['method'],
            'url': url,
            'file': file,
            'file_size': file_size,
        })
        response['headers'].update({
                'Content-Type': mimetype,
                'Content-Length': file_size,
        })
        return response

    def do_ERROR(self, raw_response):
        self.send_data(self.create_response(raw_response))

    def do_HEAD(self, raw_response):
        self.send_data(self.create_response(raw_response))

    def do_GET(self, raw_response):
        self.send_data(
            self.create_response(raw_response),
            file=raw_response.get('file'),
            file_size=raw_response.get('file_size'),
        )

    def create_response(self, response):
        if not isinstance(self.line_separator, str):
            raise ValueError('line_separator should be a string! not {}'.format(type(self.line_separator)))

        first_line = '{} {} {}'.format(PROTOCOL_VERSION, response['code'], RESPONSE_CODES[response['code']])
        headers = self.line_separator.join('{}: {}'.format(k, v) for k, v in response['headers'].items())

        return bytearray('{}{}{}{}'.format(
            first_line,
            self.line_separator,
            headers,
            self.termination
        ))

    def recv_data(self):
        buf = bytearray(b'')
        while True:
            data = self.conn.recv(self.buf_size)
            if not data:
                break
            if self.termination in buf[len(self.termination)-1:] + data:
                buf += data
                break
            buf += data
        return str(buf)

    def send_data(self, data, file=None, file_size=None):
        logging.debug("Response to {}{}\n{}<file: {}>".format(self.client_address,
                                                    self.debug_info,
                                                    data,
                                                    file))
        if not isinstance(data, bytearray):
            data = bytearray(data)
        buf = bytearray()

        if file:
            fd = io.open(file, 'rb')

        try:
            while True:
                if data:
                    buf += data[:self.buf_size]
                    data = data[self.buf_size:]
                if file:
                    buf += fd.read(self.buf_size-len(buf))
                if not buf:
                    break

                chuck = self.conn.send(buf)
                buf = buf[chuck:]
        finally:
            if file: fd.close()


############### MAIN ###############

def main(host, port, root_dir, workers):
    root_dir = os.path.abspath(root_dir)
    multi_socket = True if workers > 1 else False
    
    logging.info('Starting server at {} port with {} workers:'.format(port, workers))

    processes = []
    try:
        for i in range(workers):
            server = ThreadHTTPServer(host, port, root_dir, RequestHandler)
            p = multiprocessing.Process(target=server.serve_forever)
            processes.append(p)
            p.start()
            logging.info('Worker {} started with PID: {}'.format(i+1, p.pid))
        for p in processes:
            p.join()
    except (KeyboardInterrupt, SystemExit):
        for process in processes:
            if process:
                pid = process.pid
                logging.info('Trying to shutting down process {}'.format(pid))
                process.terminate()
                logging.info('Process {} terminated...'.format(pid))
    finally:
        logging.info('Server stopped.')


if __name__ == '__main__':
    args = parse_args()
    config = load_config(CONFIG, args.config)
    config = update_config_with_parse_args(config, args)
    setup_logger(args.logfile or config['LOGGING_FILE'], level=LOGGING_LEVEL)
    try:
        main(config['BIND_HOST'], config['BIND_PORT'],
             config['DOCUMENT_ROOT'], workers = config['WORKERS'])
    except Exception as e:
        logging.exception(e)
