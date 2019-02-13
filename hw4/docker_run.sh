# Run CentOS in docker for testing server
docker run -ti --rm -p 8080:8080 -p 80:80 -v /Users/smurov/Desktop/OTUS_Python/otus-python-homework/hw4:/web centos /bin/bash