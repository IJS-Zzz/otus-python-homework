# Log Analyzer
Script for parse and analyze ui_logs.

### Prerequisites
Python version 2.7 and above

### How to run: 
Print in terminal:
```
cd %path_to_module_dir%
python log_analyzer.py
```

If you want run script with custom config file use '--config' key.
```
cd %path_to_module_dir%
python log_analyzer.py --config %path_to_config_file%
```
Where:
* %path_to_module_dir% - path to directory with module
* %path_to_config_file% - path to config file

Custom config file must be in JSON format.
You can see sample in 'config.json.example' file.

Config parameters are:
    * REPORT_SIZE - parameter to filter report data. Only urls with total request time > report_size are selected
    * MAX_LOG_ERRORS_PERCENT – Max allowed log errors percentage
    * LOG_DIR - directory with logfiles. These files are source for the script
    * REPORT_DIR - directory where reports are stored
    * 
    * LOGGING_FILE - directory where we store the file with all events occurred during the script execution

Example:
```
{
    "REPORT_SIZE": 1000,
    "MAX_LOG_ERRORS_PERCENT": 10,
    "LOG_DIR": "./log"
    "REPORT_DIR": "./reports",
    "LOGGING_FILE": "monitoring.txt"
}
```
Config file may be empty. Then the script will use default setting:
    * "REPORT_SIZE": 1000,
    * "MAX_LOG_ERRORS_PERCENT": None,  # Percentage of Error
    * "LOG_DIR": "./log",
    * "REPORT_DIR": "./reports",
    * "REPORT_TEMPLATE": "./report.html",
    * "REPORT_TEMPLATE_NAME": "report-{}.html",
    * "LOGGING_FILE": None,
```
{}
```

### How to run tests: 
Print in terminal:
```
cd %path_to_module_dir%
python -m unittest test
```
Where:
* %path_to_module_dir% - path to directory with module

### Log Format
The script analyzes log files with filename like this:
* nginx-access-ui.log-20170630
* nginx-access-ui.log-20180515.gz
* nginx-access-ui.log-%date%
Where:
* %date% – date in format '%Y%m%d'

Format of log line:
```
log_format ui_short '$remote_addr $remote_user  '
                    '$http_x_real_ip [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for" '
                    '"$http_X_REQUEST_ID" "$http_X_RB_USER" '
                    '$request_time';
```
Sample of log line:
```
1.196.116.32 -  - [29/Jun/2017:03:50:22 +0300] "GET /api/v2/banner/25019354 HTTP/1.1" 200 927 "-" "Lynx/2.8.8dev.9 libwww-FM/2.14 SSL-MM/1.4.1 GNUTLS/2.10.5" "-" "1498697422-2190034393-4708-9752759" "dc7161be3" 0.390
```
