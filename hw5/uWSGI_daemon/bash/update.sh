#!/usr/bin/env bash

# bash /home/box/bash/update.sh

mkdir -p /usr/local/ip2w
yes | cp /home/box/ip2w.py /usr/local/ip2w/ip2w.py
yes | cp /home/box/ip2w.ini /usr/local/etc/ip2w.ini
yes | cp /home/box/ip2w.service /usr/lib/systemd/system/ip2w.service

mkdir -p /run/uwsgi
chown root:nginx /run/uwsgi
mkdir -p /var/log/ip2w

# yes | cp /home/box/nginx_ip2w.conf /etc/nginx/conf.d/nginx_ip2w.conf
yes | cp /home/box/nginx.conf /etc/nginx/nginx.conf

# nginx -s stop
# nginx

# uwsgi --ini /usr/local/etc/ip2w.ini
