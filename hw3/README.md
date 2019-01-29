# Scoring API
Implementation of the declarative language of description 
and the system of validating requests to the HTTP service API scoring.

### Requirements
Python version 2.7 and above.

### How to run:
###### Simple run:
Print in terminal:
```
cd %path_to_module_dir%
python api.py
```
The server runs on default port (8080).

Where:
* %path_to_module_dir% - path to directory with module

###### Run with keys:
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

### How to run tests: 
Print in terminal:
```
cd %path_to_module_dir%
python test.py
```

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

:rocket: