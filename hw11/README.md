# Ycrawler
Async crawler for news.ycombinator.com.<br>
Crawler check top news and saves the web pages <br>of these news and urls from comments to local folder.

### Requirements
Python version 3.7 and above.

packages:
* aiohttp
* beautifulsoup4

### Installing
```
pip install -r requirements.txt
```

### How to run
```
>>> python ycrawler.py
optional arguments:
  -h, --help                show this help message and exit
  --store_dir STORE_DIR     Path to folder for save content.
  --period PERIOD           Number of seconds between poll.
  --log                     Enable logging.
  --log_path LOG_PATH       Path to logging file.
  -v, --verbose             Verbose logging.
```
