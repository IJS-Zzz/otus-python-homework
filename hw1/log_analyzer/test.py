#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import unittest
import datetime
import logging
import io

app = __import__('log_analyzer')

logging.disable(logging.CRITICAL)


class TestFindLastLog(unittest.TestCase):
    def setUp(self):
        self.today = datetime.date.today()
        self.test_dir = './test_find_last_log-{}'.format(
            datetime.date.today().strftime("%Y%m%d"))
        self.test_dir_wrong = os.path.join(self.test_dir, 'wrong')
        self.template_filename = 'nginx-access-ui.log-{date}{gz}'
        self.last_log_filename = self.template_filename.format(
            date = self.today.strftime("%Y%m%d"),
            gz='.gz')
        self.last_log_path = os.path.join(self.test_dir,
                                          self.last_log_filename)
        # create test folders
        self.create_test_folder(self.test_dir)
        self.create_test_folder_wrong(self.test_dir_wrong)
        # create last log file
        open(self.last_log_path, 'wb').close()

    def tearDown(self):
        # remove test folder wrong
        for file in os.listdir(self.test_dir_wrong):
            os.remove(os.path.join(self.test_dir_wrong, file))
        os.removedirs(self.test_dir_wrong)

        for file in os.listdir(self.test_dir):
            os.remove(os.path.join(self.test_dir, file))
        os.removedirs(self.test_dir)

    def create_test_folder(self, path):
        if not os.path.isdir(path):
            os.makedirs(path)
        # create others log files
        for i in range(5, 30, 5):
            gz = '.gz' if i%2 == 0 else ''
            date = self.today - datetime.timedelta(days=i)
            fileneme = self.template_filename.format(
                date = date.strftime("%Y%m%d"),
                gz=gz)
            open(os.path.join(path, fileneme), 'wb').close()

    def create_test_folder_wrong(self, path):
        if not os.path.isdir(path):
            os.makedirs(path)
        # create others log files
        for i in range(3, 10):
            gz = '.gz' if i%2 == 0 else ''
            fileneme = self.template_filename.format(
                date = str(i)*8,
                gz=gz)
            open(os.path.join(path, fileneme), 'wb').close()

    #### Tests ####

    def test_get_latest_log_info(self):
        file_info = app.get_latest_log_info(self.test_dir)
        # check correct date
        self.assertEqual(
            file_info.file_date.strftime("%Y%m%d"),
            self.today.strftime("%Y%m%d"))
        # check correct file path
        self.assertEqual(
            file_info.file_path,
            self.last_log_path)

    def test_get_latest_log_info_with_wrong_names(self):
        file_info = app.get_latest_log_info(self.test_dir_wrong)
        self.assertEqual(file_info, None)


class TestParseLogLine(unittest.TestCase):
    def test_empty_line(self):
        log_line = ""
        result = app.parse_log_line(log_line)
        self.assertEqual(result, None)

    def test_bad_time(self):
        log_line = '1.194.135.240 -  - [29/Jun/2017:10:15:45 +0300] ' \
                   '"HEAD /slots/3938/ HTTP/1.1" 302 0 "-" ' \
                   '"Microsoft Office Excel 2013" "-" ' \
                   '"1498720545-244168387-4707-10016820" "-" 0.ABC0'

        result = app.parse_log_line(log_line)
        self.assertEqual(result, None)

    def test_correct_line(self):
        log_line = '1.196.116.32 -  - [29/Jun/2017:03:50:22 +0300] ' \
                   '"GET /api/v2/banner/25019354 HTTP/1.1" 200 927 ' \
                   '"-" "Lynx/2.8.8dev.9 libwww-FM/2.14 SSL-MM/1.4.1 GNUTLS/2.10.5" ' \
                   '"-" "1498697422-2190034393-4708-9752759" "dc7161be3" ' \
                   '0.390'
        result = app.parse_log_line(log_line)
        self.assertEqual(result, ('/api/v2/banner/25019354', 0.390))


class TestReportData(unittest.TestCase):
    def test_get_report_data(self):
        input_data = [
            ('/index', 0.123),
            ('/index', 0.321),
            ('/index', 0.456),
            ('/index', 0.678),
            ('/index', 0.900),

            ('/home', 0.100),
            ('/home', 0.200),
            ('/home', 0.300),
            ('/home', 0.400)
        ]

        out_data = [
            {'url': '/index',
             'count': 5,
             'time_avg': 0.496,
             'time_max': 0.9,
             'time_sum': 2.478,
             'time_med': 0.456,
             'time_perc': 71.248,
             'count_perc': 55.556},

            {'url': '/home',
             'count': 4,
             'time_avg': 0.25,
             'time_max': 0.4,
             'time_sum': 1.0,
             'time_med': 0.25,
             'time_perc': 28.752,
             'count_perc': 44.444}
        ]
        result = app.get_report_data(input_data)
        self.assertEqual(result, out_data)


class TestRenderTemplate(unittest.TestCase):
    def setUp(self):
        # $table_json - place for insert
        # in template in render_template function
        self.template = "data is: $table_json"
        self.template_file_path = "./test_template.txt"
        self.report_file_path = "./test_report.txt"

        with io.open(self.template_file_path, 'wb') as file:
            file.write(self.template)

    def tearDown(self):
        os.remove(self.template_file_path)
        os.remove(self.report_file_path)

    def test_render_template_string(self):
        data = "THIS IS SOME DATA"
        output_data = self.template.replace('$table_json',
                                            '"THIS IS SOME DATA"')
        app.render_template(self.template_file_path,
                            self.report_file_path,
                            data)
        with io.open(self.report_file_path, 'rb') as file:
            output = file.read()
            self.assertEqual(output, output_data)

    def test_render_template_list(self):
        data = [1, 2, 3, {'a':'b', 'c': 'd'}]
        output_data = self.template.replace('$table_json',
                                            '[1, 2, 3, {"a": "b", "c": "d"}]')
        app.render_template(self.template_file_path,
                            self.report_file_path,
                            data)
        with io.open(self.report_file_path, 'rb') as file:
            output = file.read()
            self.assertEqual(output, output_data)


if __name__ == '__main__':
    unittest.main()
