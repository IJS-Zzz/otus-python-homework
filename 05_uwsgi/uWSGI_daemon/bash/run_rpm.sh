#!/usr/bin/env bash

set -xe

yum localinstall -y /home/box/ip2w-0.0.1-1.noarch.rpm
mkdir -p /run/uwsgi
chown root:nginx /run/uwsgi
mkdir -p /var/log/ip2w

yes | cp /home/box/nginx.conf /etc/nginx/nginx.conf

nginx

uwsgi --ini /usr/local/etc/ip2w.ini