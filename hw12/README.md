# MemcLoad v2
GO version of memc_load.py

## How to run
### Build
```
> go build memc_load.go
```
### Run Tests
```
> go test
```
### Run Options
```
> ./memc_load --help

Usage: memc_load [options]

options:
  -dry                  debug mode (without sending to memcached)
  -workers int          number of file in parallel processing (default number of CPU)
  -buffer int           upload buffer (default 1000)

  -log                  enable write logging
  -logpath string       path to log file (default "./memc.log")
  -pattern string       files path pattern (default "/data/appsinstalled/*.tsv.gz")

  -adid string          ip and port of dvid memcached server (default "127.0.0.1:33015")
  -dvid string          ip and port of dvid memcached server (default "127.0.0.1:33016")
  -gaid string          ip and port of dvid memcached server (default "127.0.0.1:33014")
  -idfa string          p and port of idfa memcached server (default "127.0.0.1:33013")
```

## Brenchmarks
### Test data description:
```
> ls -al
[...]
-rw-r--r-- 1 root root 507M Apr 12 07:54 20170929000000.tsv.gz
-rw-r--r-- 1 root root 507M Apr 12 08:17 20170929000100.tsv.gz
-rw-r--r-- 1 root root 507M Apr 12 08:26 20170929000200.tsv.gz
[...]
```
### Execution time:
```
> time go run memc_load.go -pattern=$(pwd)/data/*.tsv.gz -dry

real    1m19.605s
user    1m38.350s
sys 0m28.430s
```

