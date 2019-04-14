# MemcLoad
Multiprocessing version of memc_load.py.<br>
Multi-threaded on N workers.<br>
Each worker processes one file at a time. <br>
Main thread of process parses from given a file <br>
info about user's installed apps and load to queue. <br>
For each memcache address create thread for upload data.

### Requirements
- Python 2.7
- python-memcached
- protobuf

### How to run
```
> python memc_load_multi.py --help

Usage: memc_load_multi.py [options]

Options:
  -h, --help            show this help message and exit
  -t, --test            
  -l LOG, --log=LOG     
  -w WORKERS, --workers=WORKERS
  --dry                 
  --pattern=PATTERN     
  --idfa=IDFA           
  --gaid=GAID           
  --adid=ADID           
  --dvid=DVID    
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
### Single thread handler execution time:
```
>time python memc_load.py --pattern=$(pwd)/data/*.tsv.gz --dry

real    25m49.317s
user    22m7.790s
sys 3m34.600s
```
### N-workers multi-threaded handler execution time:
```
time python memc_load_multi.py --workers=2 --pattern=$(pwd)/data/*.tsv.gz --dry

real    12m14.422s
user    14m15.750s
sys 3m39.350s
```