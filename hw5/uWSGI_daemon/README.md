# ip2w Server
Simple Python application based on uWSGI.

### Requirements
Python version 2.7 and above.
Python packages:
* requests

### Stack
nginx + uWSGI + ip2w

### Run
Please set WEATHER_APPID in environment variables.
WEATHER_APPID is api_key from openweathermap.org

ip2w server write logs in /var/log/ip2w/ip2w-error.log files.

### Example
```
curl http://localhost/ip2w/176.14.221.123
{"city": "Moscow", "temp": "+20", "conditions": "небольшой дождь"}
```
