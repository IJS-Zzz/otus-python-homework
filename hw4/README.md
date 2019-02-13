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
2 workers 25000 requests
```
Server Software:        OtusServer
Server Hostname:        127.0.0.1
Server Port:            80

Document Path:          /httptest/dir2/index.html
Document Length:        34 bytes

Concurrency Level:      100
Time taken for tests:   104.638 seconds
Complete requests:      25000
Failed requests:        0
Total transferred:      4350000 bytes
HTML transferred:       850000 bytes
Requests per second:    238.92 [#/sec] (mean)
Time per request:       418.552 [ms] (mean)
Time per request:       4.186 [ms] (mean, across all concurrent requests)
Transfer rate:          40.60 [Kbytes/sec] received

Connection Times (ms)
              min  mean[+/-sd] median   max
Connect:        0    0   0.3      0       5
Processing:    15  417 230.4    403    1981
Waiting:       13  408 225.9    395    1941
Total:         15  417 230.4    403    1981

Percentage of the requests served within a certain time (ms)
  50%    403
  66%    500
  75%    569
  80%    608
  90%    703
  95%    776
  98%    882
  99%    998
 100%   1981 (longest request)
```
5 workers 50000 requests

```
Server Software:        OtusServer
Server Hostname:        127.0.0.1
Server Port:            80

Document Path:          /httptest/dir2/index.html
Document Length:        34 bytes

Concurrency Level:      100
Time taken for tests:   180.044 seconds
Complete requests:      50000
Failed requests:        0
Total transferred:      8700000 bytes
HTML transferred:       1700000 bytes
Requests per second:    277.71 [#/sec] (mean)
Time per request:       360.087 [ms] (mean)
Time per request:       3.601 [ms] (mean, across all concurrent requests)
Transfer rate:          47.19 [Kbytes/sec] received

Connection Times (ms)
              min  mean[+/-sd] median   max
Connect:        0    1 101.8      0   22764
Processing:    10  359 219.7    320    2140
Waiting:        8  349 215.3    311    1851
Total:         10  360 242.9    320   23528

Percentage of the requests served within a certain time (ms)
  50%    320
  66%    413
  75%    480
  80%    525
  90%    655
  95%    777
  98%    918
  99%   1026
 100%  23528 (longest request)
```
