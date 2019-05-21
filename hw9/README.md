# MemcLoad
Multiprocessing version of memc_load.py.

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
> time python memc_load.py --pattern=$(pwd)/data/*.tsv.gz --dry

real    25m49.317s
user    22m7.790s
sys 3m34.600s
```
### N-workers multi-threaded handler execution time:
```
> time python memc_load_multi.py --pattern=$(pwd)/data/*.tsv.gz --dry

real  4m19.334s
user  7m45.020s
sys 0m28.490s
```