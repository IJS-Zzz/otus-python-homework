# Scoring API
Implementation of the declarative language of description 
and the system of validating requests to the HTTP service API scoring.
The script processes POST request for online scoring or users interests.

### Requirements
Python version 2.7 and above.
packages:
* redis
* requests

##### Other software
The script works with Redis db at 'localhost:6379'.
If you have installed Docker you can run Redis server in docker container.
Use next bash scripts:
* run_redis_in_docker.sh
* stop_redis_in_docker.sh
Run docker container with Redis:
```
cd %path_to_module_dir%
bash run_redis_in_docker.sh
```
Stop docker container with Redis:
```
cd %path_to_module_dir%
bash stop_redis_in_docker.sh
```
Note: run_redis_in_docker.sh contains '-rm' running key for remove all data after stop docker container.
Where:
* %path_to_module_dir% - path to directory with module

### How to run:
##### Simple run:
Print in terminal:
```
cd %path_to_module_dir%
python api.py
```
The server runs on default port (8080).

##### Run with keys:
Available keys:
* "-p", "--port" – Run server on custom port. (arg example: %port%)
* "-l", "--log" – Write output logs in file. (arg example: %path_to_output_logs_file%)

Print in terminal:
```
cd %path_to_module_dir%
python api.py %key% %value%
```
Where:
* %key% – running key
* %value% – value of key
* %port% – listening post of server
* %path_to_output_logs_file% – path to output logs file

### Work:
To get the result, the user sends in the POST request valid JSON defined format to 'location/method'.
API has next methods to work with user data:
* _online_score_ method
* _client_interests_ method

### Request samples
Sample for _online_score_ method:
```
curl -X POST -H "Content-Type: application/json" -d '{
    "account": "horns&hoofs",
    "login": "h&f",
    "method": "online_score",
    "token": "55cc9ce545bcd144300fe9efc28e65d415b923ebb6be1e19d2750a2c03e80dd209a27954dca045e5bb12418e7d89b6d718a9e35af34e14e1d5bcd5a08f21fc95",
    "arguments": {
        "phone": "79998887766",
        "email": "example@mail.com",
        "first_name": "FirstName",
        "last_name": "LastLame",
        "birthday": "01.01.2000",
        "gender": 1
    }
}' http://127.0.0.1:8080/method/
```

Sample for _client_interests_ method:
```
curl -X POST -H "Content-Type: application/json" -d '{
    "account": "horns&hoofs",
    "login": "h&f",
    "method": "clients_interests",
    "token": "55cc9ce545bcd144300fe9efc28e65d415b923ebb6be1e19d2750a2c03e80dd209a27954dca045e5bb12418e7d89b6d718a9e35af34e14e1d5bcd5a08f21fc95",
    "arguments": {
        "client_ids": [1,2,3,4],
        "date": "20.07.2017"
    }
}' http://127.0.0.1:8080/method/
```

### How to run tests:
Available two type of tests:
* Unit test
* Integration test

#### Unit test
Tests:
* test_fields – this script are unittest for every field class object.
* test_requests – unittest for every requests class object.
* test_scoring – unittest for scoring module.
* test_functional – test different scenarios of requests

Run Unit tests:
```
cd %path_to_module_dir%
bash run_tests_unit.sh
```
or the same
```
cd %path_to_module_dir%
python -m unittest discover -v -s ./tests/unit
```

#### Integration test
Tests:
* test_integration – this script request the data from running server and test different scenarios of requests.

Before running this test you have to run HTTP-server of scoring with the following parameters:
* ip-address http://127.0.0.1
* port 8080

Run Integration tests:
```
cd %path_to_module_dir%
bash run_tests_integration.sh
```
or the same
```
cd %path_to_module_dir%
python -m unittest discover -v -s ./tests/integration
```

#### Run All Tests
Run Integration tests:
```
cd %path_to_module_dir%
bash run_all_tests.sh
```
or the same
```
cd %path_to_module_dir%
python -m unittest discover -v -s ./tests/
```

:rocket: