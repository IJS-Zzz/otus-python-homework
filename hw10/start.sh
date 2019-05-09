#!/bin/sh
set -xe

yum update -y
yum install -y epel-release
yum install -y  gcc \
                make \
                protobuf \
                protobuf-c \
                protobuf-c-compiler \
                protobuf-c-devel \
                python-pip \
                python-devel \
                python-setuptools \
                gdb \
                zlib-devel

ulimit -c unlimited
cd /tmp/otus/
protoc-c --c_out=. deviceapps.proto
protoc --python_out=. deviceapps.proto
pip install -U protobuf
python setup.py test
