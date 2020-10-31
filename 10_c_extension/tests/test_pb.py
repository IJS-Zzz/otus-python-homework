import os
import unittest
import gzip
import struct
import deviceapps_pb2

import pb
MAGIC = 0xFFFFFFFF
DEVICE_APPS_TYPE = 1
TEST_FILE = "test.pb.gz"

TEST_EMPTY_FILE = "test_empty_file.pb.gz"


class TestPB(unittest.TestCase):
    deviceapps = [
        {"device": {"type": "idfa", "id": "e7e1a50c0ec2747ca56cd9e1558c0d7c"},
         "lat": 67.7835424444, "lon": -22.8044005471, "apps": [1, 2, 3, 4]},
        {"device": {"type": "gaid", "id": "e7e1a50c0ec2747ca56cd9e1558c0d7d"}, "lat": 42, "lon": -42, "apps": [1, 2]},
        {"device": {"type": "gaid", "id": "e7e1a50c0ec2747ca56cd9e1558c0d7d"}, "lat": 42, "lon": -42, "apps": []},
        {"device": {"type": "gaid", "id": "e7e1a50c0ec2747ca56cd9e1558c0d7d"}, "apps": [1]},
        {"device": {"id": "e7e1a50c0ec2747ca56cd9e1558c0d7d"}, "apps": []},
        {"apps": [99, 56]},
        {"lat": 14, "apps": []},
    ]

    def tearDown(self):
        if os.path.exists(TEST_FILE):
            os.remove(TEST_FILE)
        if os.path.exists(TEST_EMPTY_FILE):
            os.remove(TEST_EMPTY_FILE)

    # Test Write
    def test_write(self):
        bytes_written = pb.deviceapps_xwrite_pb(self.deviceapps, TEST_FILE)
        self.assertTrue(bytes_written > 0)

        # Test Data
        header_size = 8
        with gzip.open(TEST_FILE, 'rb') as f:
            for deviceapp in self.deviceapps:
                # Test Header
                header = f.read(header_size)
                magic, dev_apps_type, length = struct.unpack('<IHH', header)
                self.assertEqual(magic, MAGIC)
                self.assertEqual(dev_apps_type, DEVICE_APPS_TYPE)

                # Test Body
                raw_data = f.read(length)
                data = deviceapps_pb2.DeviceApps()
                data.ParseFromString(raw_data)
                self.assertEqual(data.device.id, deviceapp.get('device', {}).get('id', ''))
                self.assertEqual(data.device.type, deviceapp.get('device', {}).get('type', ''))
                self.assertEqual(data.lat, deviceapp.get('lat', 0))
                self.assertEqual(data.lon, deviceapp.get('lon', 0))
                self.assertEqual(data.apps, deviceapp.get('apps', []))

    # Test Read
    def test_read(self):
        pb.deviceapps_xwrite_pb(self.deviceapps, TEST_FILE)
        for i, d in enumerate(pb.deviceapps_xread_pb(TEST_FILE)):
            self.assertEqual(d, self.deviceapps[i])

    # Test Write Exceptions

    def test_write_raise_value_error_if_first_argument_is_not_iterable(self):
        devapps = 12
        with self.assertRaisesRegexp(ValueError, "First argument should be iterable"):
            pb.deviceapps_xwrite_pb(devapps, TEST_FILE)

    def test_write_raise_value_error_if_item_in_deviceapps_list_is_not_dict(self):
        devapps = [1, 2, 3]
        with self.assertRaisesRegexp(ValueError, "Item in list of 'deviceapps' must be a dictionary type"):
            pb.deviceapps_xwrite_pb(devapps, TEST_FILE)

    def test_write_raise_value_error_if_device_is_not_dict(self):
        devapps = [{"device": 123.00}]
        with self.assertRaisesRegexp(ValueError, "'device' must be a dictionary type"):
            pb.deviceapps_xwrite_pb(devapps, TEST_FILE)

    def test_write_raise_value_error_if_id_is_not_string(self):
        devapps = [{"device": {"type": "gaid", "id": 123}}]
        with self.assertRaisesRegexp(ValueError, "'id' must be a string type"):
            pb.deviceapps_xwrite_pb(devapps, TEST_FILE)

    def test_write_raise_value_error_if_type_is_not_string(self):
        devapps = [{"device": {"type": 123, "id": "e7e1a50c0ec2747ca56cd9e1558c0d7d"}}]
        with self.assertRaisesRegexp(ValueError, "'type' must be a string type"):
            pb.deviceapps_xwrite_pb(devapps, TEST_FILE)

    def test_write_raise_value_error_if_lat_is_not_integer_or_float(self):
        devapps = [{"lat": {"type": 123, "id": "e7e1a50c0ec2747ca56cd9e1558c0d7d"}}]
        with self.assertRaisesRegexp(ValueError, "'lat' must be a float or an integer type"):
            pb.deviceapps_xwrite_pb(devapps, TEST_FILE)

    def test_write_raise_value_error_if_lon_is_not_integer_or_float(self):
        devapps = [{"lon": "66"}]
        with self.assertRaisesRegexp(ValueError, "'lon' must be a float or an integer type"):
            pb.deviceapps_xwrite_pb(devapps, TEST_FILE)
    
    def test_write_raise_value_error_if_apps_is_not_list(self):
        devapps = [{"apps": "1, 2, 3"}]
        with self.assertRaisesRegexp(ValueError, "'apps' must be a list type"):
            pb.deviceapps_xwrite_pb(devapps, TEST_FILE)
    
    def test_write_raise_value_error_if_app_in_apps_is_not_integer(self):
        devapps = [{"apps": [12.234, "234"]}]
        with self.assertRaisesRegexp(ValueError, "'app' must be an integer type"):
            pb.deviceapps_xwrite_pb(devapps, TEST_FILE)

    # Test Read Exceptions and Cases

    def test_read_file_file_does_not_exist(self):
        with self.assertRaisesRegexp(IOError, "File does not exist"):
            pb.deviceapps_xread_pb("NotExistFile")

    def test_read_empty_file(self):
        with open(TEST_EMPTY_FILE, 'wb') as f:
            res = list(pb.deviceapps_xread_pb(TEST_EMPTY_FILE))
            self.assertEqual(res, [])

    def test_read_class_and_function_have_same_result(self):
        pb.deviceapps_xwrite_pb(self.deviceapps, TEST_FILE)
        res1 = list(pb.deviceapps_xread_pb(TEST_FILE))
        res2 = list(pb.PBFileIterator(TEST_FILE))
        self.assertEqual(res1, res2)
