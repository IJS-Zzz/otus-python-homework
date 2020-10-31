# HTTP Server
HTTP server with implemented GET and HEAD methods.
Run with several listening processes on given port.

The requirements and general principles of this server was described [here](https://github.com/s-stupnikov/http-test-suite)

#### Architecture
The implementation is based on Multi-threaded on N workers.
Workers are implemented on the basis of processes using the module multiprocessing. For each user request within the selected process, a new thread is created in which the request is processed and a response is returned.

Multiprocessing scheme:
```
    httpd.py
      |
      |         workers
      |--process-->|
      |            |--thread<--->client
      |            |--thread<--->client
      |            |--thread<--->client
      |
      |--process-->|
      |            |--thread<--->client
      |            |--thread<--->client
      |            |--thread<--->client
      |
      |--process-->|
      |            |--thread<--->client
      |            |--thread<--->client
      |            |--thread<--->client
```

### Requirements
Python version 2.7 and above.

### Details
The server supports the following file types : 
  * \*.html, \*.css, \*.css.js, \*.jpg, \*.jpeg, \*.png, \*.gif, \*.swf

### How to run:
```
cd %path_to_module_dir%
python httpd.py
```
The server runs on default port (8080)
and searches files in %path_to_module_dir% directory.

##### Run with keys:
```
optional arguments:
  -h, --help         show this help message and exit
  -w WORKERS         Count of used server's workers.
  -r ROOT_DIR        Server's root directory.
  --port PORT        Port is used of the server.
  --logfile LOGFILE  File for save server logs.
  --config [CONFIG]  Config file path. Using JSON format.
                     Without value load default config (./config.json)
```


### Load Testing
AB testing results:
```
ab -n 50000 -c 100 -r http://127.0.0.1/httptest/dir2/index.html
```
2 workers 50000 requests

```
Server Software:        OtusServer
Server Hostname:        127.0.0.1
Server Port:            80

Document Path:          /httptest/dir2/index.html
Document Length:        34 bytes

Concurrency Level:      100
Time taken for tests:   296.573 seconds
Complete requests:      50000
Failed requests:        0
Total transferred:      8700000 bytes
HTML transferred:       1700000 bytes
Requests per second:    168.59 [#/sec] (mean)
Time per request:       593.145 [ms] (mean)
Time per request:       5.931 [ms] (mean, across all concurrent requests)
Transfer rate:          28.65 [Kbytes/sec] received

Connection Times (ms)
              min  mean[+/-sd] median   max
Connect:        0    0   0.2      0      19
Processing:     7  592 406.0    589    2005
Waiting:        6  591 405.9    587    2005
Total:          7  592 406.0    589    2005

Percentage of the requests served within a certain time (ms)
  50%    589
  66%    845
  75%    961
  80%   1022
  90%   1126
  95%   1183
  98%   1239
  99%   1278
 100%   2005 (longest request)
```

:rocket: