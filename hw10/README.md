
# Protobuf Serializer
C extension for Python

### Description
Extension for pack/unpack protobuf message in file.

functions:
* deviceapps_xwrite_pb – function for packing data in file
    ```
    filename = test.pb.gz
    deviceapps = [
        {"device": {"type": "idfa", "id": "e7e1a50c0ec2747ca56cd9e1558c0d7c"},
         "lat": 67.7835424444, "lon": -22.8044005471, "apps": [1, 2, 3, 4]},
        {"device": {"type": "gaid", "id": "e7e1a50c0ec2747ca56cd9e1558c0d7d"},
         "lat": 42, "lon": -42, "apps": [1, 2]},
    ]
    deviceapps_xwrite_pb(deviceapps, filename)
    ```
* deviceapps_xread_pb – function for unpacking data from file, return iterator
    ```
    filename = test.pb.gz
    iterator = deviceapps_xread_pb(filename)
    deviceapps = list(iterator)
    ```

### Requirements
Python version 2.7 and above
packages:
* protobuf