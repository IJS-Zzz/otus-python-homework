# -*- coding: utf-8 -*-

import datetime
import functools
import hashlib

from context import api


def cases(cases):
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args):
            for c in cases:
                new_args = args + (c if isinstance(c, tuple) else (c,))
                try:
                    f(*new_args)
                except Exception as e:
                    # Add info about test case in exception message
                    msg = e.message
                    info = ' (Run with args: {})'.format(c)
                    if not isinstance(msg, str):
                        msg = str(msg)
                    msg += info
                    e.args = (msg, ) + e.args[1:]
                    raise

        return wrapper
    return decorator


def gen_valid_token(login='', account=''):
    if login == api.ADMIN_LOGIN:
        return hashlib.sha512(datetime.datetime.now().strftime("%Y%m%d%H") + api.ADMIN_SALT).hexdigest()
    else:
        msg = account + login + api.SALT
        return hashlib.sha512(msg).hexdigest()


##### Mock #####

class MockRedisConnection(object):
    def __init__(self, *args, **kwargs):
        self.db = {}
        self.get_counter = 0
        self.set_counter = 0
        self.delete_counter = 0

    def get(self, key):
        self.get_counter += 1
        return self.db.get(key)

    def set(self, key, value, expires=None):
        self.set_counter += 1
        self.db[key] = value

    def delete(self, key):
        self.delete_counter += 1
        return self.db.pop(key, None)

    def clean(self):
        self.db = {}
        self.get_counter = 0
        self.set_counter = 0
        self.delete_counter = 0
