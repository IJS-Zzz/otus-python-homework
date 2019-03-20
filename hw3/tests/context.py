#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import logging

logging.disable(logging.ERROR)

app_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(app_dir, 'api'))

import api
import scoring
import store


# Load Environment Variables
API_URL = os.getenv('API_URL')

STORE_CONFIG = {}

env_vars = {
    'host': os.getenv('REDIS_HOST'),
    'port': os.getenv('REDIS_PORT'),
    'password': os.getenv('REDIS_PASSWORD'),
}

if env_vars['host']:
    STORE_CONFIG.update(api.STORE_CONFIG)
    for k, v in env_vars.items():
        if v:
            STORE_CONFIG[k] = v
