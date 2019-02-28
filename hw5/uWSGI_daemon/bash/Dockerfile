FROM centos
RUN set -e;\
    set -x;\
    yum clean all;\
    yum update -y;\
    yum install -y epel-release;\
    yum install -y git\
               make\
               gcc\
               gcc-c++\
               vim\
               ssh\
               python-pip\
               python-devel\
               nginx\
               lsof\
               rpm\
               rpm-build;\
    pip install --upgrade pip;\
    pip install -U uwsgi requests;
