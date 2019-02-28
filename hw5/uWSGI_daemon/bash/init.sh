#!/usr/bin/env bash

# Run docker command
# docker run -ti --rm -p 8080:80 -v /Users/smurov/Desktop/OTUS_Python/otus-python-homework/hw5/uWSGI_daemon:/home/box centos /bin/bash
# docker run -ti --rm -p 8080:80 -v /Users/smurov/Desktop/OTUS_Python/otus-python-homework/hw5/uWSGI_daemon:/home/box/ my_centos /bin/bash

# set -xe
set -e
set -x

yum clean all
yum update -y
yum install -y epel-release
yum install -y git\
               make\
               gcc\
               gcc-c++\
               vim\
               ssh\
               python-pip\
               python-devel\
               nginx\
               lsof

pip install --upgrade pip
pip install -U uwsgi requests
