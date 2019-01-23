#!/usr/bin/env python
# -*- coding: utf-8 -*-


import argparse
import fnmatch
import gzip
import io
import json
import logging
import os
import re

import ConfigParser as configparser


from collections import namedtuple
from datetime import datetime
from string import Template
from tempfile import NamedTemporaryFile


##### SETTINGS #####

DEFAULT_CONFIG_PATH = "./config.json"

CONFIG = {
    "REPORT_SIZE": 1000,
    "MAX_LOG_ERRORS_PERCENT": None,  # Percentage of Error
    "LOG_DIR": "./log",
    "REPORT_DIR": "./reports",
    "REPORT_TEMPLATE": "./report.html",
    "REPORT_TEMPLATE_NAME": "report-{}.html",
    "LOGGING_FILE": None,
}

LOG_FILENAME_RE = re.compile(
    r'^nginx-access-ui\.log-(?P<date>\d{8})(\.gz)?$'
)

LOG_LINE_FORMAT_RE = re.compile(
    '^'
    '\S+ '                      # remote_addr
    '\S+\s+'                    # remote_user (ends with double space!)
    '\S+ '                      # http_x_real_ip
    '\[\S+ \S+\] '              # time_local – [datetime tz]
    '"\S+ (?P<href>\S+) \S+" '  # request – "method href protocol"
    '\d+ '                       # status
    '\d+ '                       # body_bytes_sent
    '"\S+" '                     # http_referer
    '".*" '                      # http_user_agent
    '"\S+" '                     # http_x_forwarded_for
    '"\S+" '                     # http_X_REQUEST_ID
    '"\S+" '                     # http_X_RB_USER
    '(?P<time>\d+\.\d+)'        # request_time
)

# log_format ui_short '$remote_addr $remote_user  '
#                     '$http_x_real_ip [$time_local] "$request" '
#                     '$status $body_bytes_sent "$http_referer" '
#                     '"$http_user_agent" "$http_x_forwarded_for" '
#                     '"$http_X_REQUEST_ID" "$http_X_RB_USER" '
#                     '$request_time';

# Log line example:
#       '1.196.116.32 -  - [29/Jun/2017:03:50:22 +0300] ' \
#       '"GET /api/v2/banner/25019354 HTTP/1.1" 200 927 ' \
#       '"-" "Lynx/2.8.8dev.9 libwww-FM/2.14 SSL-MM/1.4.1 GNUTLS/2.10.5" ' \
#       '"-" "1498697422-2190034393-4708-9752759" "dc7161be3" '
#       '0.390'


##### SERVICE #####

def parse_args():
    parser = argparse.ArgumentParser(description="Server's Log Analyzer")
    parser.add_argument(
        '--config',
        nargs='?',
        const=DEFAULT_CONFIG_PATH,
        help="Config file path. Using JSON format.")

    return parser.parse_args()


def load_config(config, conf_path=None):
    if not conf_path:
        return config

    with io.open(conf_path, 'rb') as file:
        config.update(json.load(file, encoding='utf8'))
    return config


def setup_logger(logging_file=None):
    logging.basicConfig(
        filename=logging_file,
        format='[%(asctime)s] %(levelname).1s %(message)s',
        datefmt='%Y.%m.%d %H:%M:%S',
        level=logging.INFO)


##### LOG PARSE #####

def get_latest_log_info(files_dir):
    if not os.path.isdir(files_dir):
        logging.info("Log directory '{}' doesn't exist".format(files_dir))
        return

    DateNamedFileInfo = namedtuple('DateNamedFileInfo', ['file_path', 'file_date'])

    latest_file_info = None

    for filename in os.listdir(files_dir):
        match = LOG_FILENAME_RE.match(filename)
        if not match:
            continue

        date_string = match.groupdict()['date']
        try:
            file_date = datetime.strptime(date_string, '%Y%m%d')
        except ValueError:
            continue

        if not latest_file_info or file_date > latest_file_info.file_date:
            latest_file_info = DateNamedFileInfo(file_path=os.path.join(files_dir,filename),
                                                 file_date=file_date)
    if not latest_file_info:
        logging.info('Ooops. No log files yet.')
    return latest_file_info


def get_log_records(file_path, errors_limit=None):
    opener = gzip.open if file_path.endswith('.gz') else io.open
    errors = 0
    records = 0

    with opener(file_path, mode='rb') as log_file:
        for line in log_file:
            records += 1
            line = line.decode('utf8')
            record = parse_log_line(line)
            if not record:
                errors += 1
                continue

            yield record

    errors_percent = int(round(errors / float(records) * 100))
    logging.info(
        'Processed {} records. ' \
        'Percent of errors in records is {}%.'.format(records, errors_percent))

    if (errors_limit is not None
        and records > 0
        and errors_percent > errors_limit):
        raise RuntimeError('Errors limit exceeded.')


def parse_log_line(log_line):
    match = LOG_LINE_FORMAT_RE.match(log_line)
    if not match:
        return

    href = match.groupdict()['href']
    request_time = float(match.groupdict()['time'])

    return href, request_time


##### LOG ANALYZE #####

def get_report_data(records, report_size=None):
    total_records = 0
    total_time = 0
    intermediate_data = {}

    for href, time in records:
        total_records += 1
        total_time += time
        create_or_updare_intermediate_item(intermediate_data, href, time)

    data = sorted(intermediate_data.values(), key=lambda i: i['request_total_time'], reverse=True)
    data = data[:report_size]

    return [create_result_item(item, total_records, total_time) for item in data]


def create_or_updare_intermediate_item(intermediate_data, href, time):
    item = intermediate_data.get(href)
    if not item:
        item = {
            'href': href,
            'request_count': 0,
            'request_total_time': 0,
            'request_max_time': 0,
            'request_avg_time': 0,
            'request_time_list': []
        }
    item['request_count'] += 1
    item['request_total_time'] += time
    item['request_max_time'] = max(time, item['request_max_time'])
    item['request_avg_time'] = item['request_total_time'] / float(item['request_count'])
    item['request_time_list'].append(time)

    intermediate_data[href] = item


def create_result_item(intermediate_item, total_records, total_time):
    url = intermediate_item['href']
    count = intermediate_item['request_count']
    count_perc = intermediate_item['request_count'] / float(total_records) * 100
    time_avg = intermediate_item['request_avg_time']
    time_max = intermediate_item['request_max_time']
    time_med = calculate_median(intermediate_item['request_time_list'])
    time_perc = intermediate_item['request_total_time'] / float(total_time) * 100
    time_sum = intermediate_item['request_total_time']

    return {
        "url": url,
        "count": count,
        "count_perc": round(count_perc, 3),
        "time_avg": round(time_avg, 3),
        "time_max": round(time_max, 3),
        "time_med": round(time_med, 3),
        "time_perc": round(time_perc, 3),
        "time_sum": round(time_sum, 3),
    }


def calculate_median(values):
    values = sorted(values)
    length = len(values)

    if length < 1:
        return None
    if length % 2 == 1:
        return values[length//2]
    else:
        return sum(values[length//2-1:length//2+1])/2.0


##### REPORT RENDER #####

def render_template(template_file_path, report_file_path, data):
    if not data:
        data = []

    report_dir = os.path.dirname(report_file_path)
    if not os.path.isdir(report_dir):
        os.makedirs(report_dir)

    if not os.path.isfile(template_file_path):
        logging.error("Report template file doesn't exist!")
        raise RuntimeError("Please check your report template file.")

    with io.open(template_file_path, 'rb') as template_file:
        template_string = template_file.read().decode('utf8')
        template = Template(template_string)

    html_report = template.safe_substitute(table_json=json.dumps(data))

    with NamedTemporaryFile(mode='w+b', dir=report_dir) as temp_file:
        html_report.encode('utf8')
        temp_file.write(html_report)
        temp_file.flush()

        # save output file after after completion of write temp file
        os.link(temp_file.name, report_file_path)


##### MAIN #####

def main(config):
    # resolving an actual log
    latest_log_info = get_latest_log_info(config['LOG_DIR'])
    if not latest_log_info:
        return

    report_date_string = latest_log_info.file_date.strftime('%Y.%m.%d')
    report_filename = config['REPORT_TEMPLATE_NAME'].format(report_date_string)
    report_file_path = os.path.join(config['REPORT_DIR'], report_filename)

    if os.path.isfile(report_file_path):
        logging.info('Looks like everything is up-to-date.')
        return

    # report creation
    logging.info('Collecting data from "{}"'.format(os.path.normpath(report_file_path)))
    log_records = get_log_records(latest_log_info.file_path,
                                  config['MAX_LOG_ERRORS_PERCENT'])
    report_data = get_report_data(log_records, config['REPORT_SIZE'])

    render_template(config['REPORT_TEMPLATE'], report_file_path, report_data)

    logging.info('Report saved to {}.'.format(os.path.normpath(report_file_path)))


if __name__ == '__main__':
    args = parse_args()
    config = load_config(CONFIG, args.config)
    setup_logger(config.get("LOGGING_FILE"))
    try:
        main(config)
    except Exception as ex:
        logging.exception(ex)
