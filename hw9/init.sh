# For CentOS 7
# docker run --rm -it -v $(pwd):/home/box centos /bin/bash

yum clean all
yum update -y
yum install -y epel-release
yum install -y git\
               make\
               gcc\
               gcc-c++\
               vim\
               python-pip\
               python-devel\
               lsof \
               memcached \
               protobuf

pip install --upgrade pip
pip install -U  protobuf \
                python-memcached
