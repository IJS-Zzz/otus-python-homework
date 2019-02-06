# -*- coding: utf-8 -*-

import unittest
from datetime import datetime

from context import api
from utils import cases


class TestBaseField(unittest.TestCase):
    @cases([
        api.CharField,
        api.ArgumentsField,
        api.EmailField,
        api.PhoneField,
        api.DateField,
        api.BirthDayField,
        api.GenderField,
        api.ClientIDsField
    ])
    def test_field_required_default_true(self, field):
        field = field()
        self.assertEqual(field.error_messages['required'], "This field is required.")
        with self.assertRaisesRegexp(api.ValidationError, r"This field is required\."):
            field.validate(None)

    @cases([
        api.CharField,
        api.ArgumentsField,
        api.EmailField,
        api.PhoneField,
        api.DateField,
        api.BirthDayField,
        api.GenderField,
        api.ClientIDsField
    ])
    def test_field_required_set_true(self, field):
        field = field()
        with self.assertRaisesRegexp(api.ValidationError, r"This field is required\."):
            field.validate(None)

    @cases([
        api.CharField,
        api.ArgumentsField,
        api.EmailField,
        api.PhoneField,
        api.DateField,
        api.BirthDayField,
        api.GenderField,
        api.ClientIDsField
    ])
    def test_field_required_set_false_and_nullable_default_false(self, field):
        field = field(required=False)
        self.assertEqual(field.error_messages['nullable'], "This field can't be empty.")
        with self.assertRaisesRegexp(api.ValidationError, r"This field can't be empty\."):
            field.validate(None)

    @cases([
        api.CharField,
        api.ArgumentsField,
        api.EmailField,
        api.PhoneField,
        api.DateField,
        api.BirthDayField,
        api.GenderField,
        api.ClientIDsField
    ])
    def test_field_required_set_false_and_nullable_set_true(self, field):
        field = field(required=False, nullable=True)
        self.assertTrue(field.validate(None))

    @cases([
        api.CharField,
        api.ArgumentsField,
        api.EmailField,
        api.PhoneField,
        api.DateField,
        api.BirthDayField,
        api.GenderField,
        api.ClientIDsField,
    ])
    def test_field_is_exist_default_false(self, field):
        field = field()
        self.assertFalse(field.is_exist)


class TestCharField(unittest.TestCase):
    def setUp(self):
        self.test_field = api.CharField

    @cases([
        '',
        'String',
        'Строка',
        '123456',
        u'',
        u'Unicode String',
        u'Юникод Строка',
        u'654321'
    ])
    def test_validation_correct_value(self, value):
        field = self.test_field(required=False, nullable=True)
        self.assertTrue(field.validate(value))

    @cases([
        123456,
        34.563,
        {'key': 'value'},
        [9, 8, 7, 6, 5],
        (('a', 'b', 'c'),)  # cases work's specific == ('a', 'b', 'c')
    ])
    def test_validation_invalid_type(self, value):
        field = self.test_field(required=False, nullable=True)
        self.assertEqual(field.error_messages['invalid_type'], "Value type must be a string.")
        with self.assertRaisesRegexp(api.ValidationError, r"Value type must be a string\."):
            field.validate(value)

    @cases([
        None,
        '',
        'String',
        'Строка',
        '123456',
        u'',
        u'Unicode String',
        u'Юникод Строка',
        u'654321',

        # other types
        {},
        {'key': 'value'},
        [],
        [9, 8, 7, 6, 5],
        ((),),
        (('a', 'b', 'c'),),
    ])
    def test_clean_data_to_unicode(self, value):
        field = self.test_field(required=False, nullable=True)
        self.assertIsInstance(field.clean(value), unicode)


class TestArgumentsField(unittest.TestCase):
    def setUp(self):
        self.test_field = api.ArgumentsField

    @cases([
        None,
        {},
        {'key': 'value'},
        {'key': 'value', 'list': [9, 8, 7, 6, 5]},
        {'value': 10, 'tuple': ('a', 'b', 'c')}
    ])
    def test_validation_correct_value(self, value):
        field = self.test_field(required=False, nullable=True)
        self.assertTrue(field.validate(value))

    @cases([
        '',
        'String',
        u'',
        u'Юникод Строка',
        123456,
        34.563,
        [],
        [9, 8, 7, 6, 5],
        ((),),
        (('a', 'b', 'c'),)  # cases work's specific == ('a', 'b', 'c')
    ])
    def test_validation_invalid_type(self, value):
        field = self.test_field(required=False, nullable=True)
        self.assertEqual(field.error_messages['invalid_type'], "Value type must be JSON object.")
        with self.assertRaisesRegexp(api.ValidationError, r"Value type must be JSON object\."):
            field.validate(value)

    @cases([
        None,
        {},
        {'key': 'value'},
        {'key': 'value', 'list': [9, 8, 7, 6, 5]},
        {'value': 10, 'tuple': ('a', 'b', 'c')}
    ])
    def test_clean_data_to_dict(self, value):
        field = self.test_field(required=False, nullable=True)
        self.assertIsInstance(field.clean(value), dict)


class TestEmailField(unittest.TestCase):
    def setUp(self):
        self.test_field = api.EmailField

    @cases([
        None,
        '',
        '123@site.com',
        u'',
        u'qwerty@asdf.ge',
    ])
    def test_validation_correct_value(self, value):
        field = self.test_field(required=False, nullable=True)
        self.assertTrue(field.validate(value))

    @cases([
        123456,
        34.563,
        [],
        [9, 8, 7, 6, 5],
        ((),),
        (('a', 'b', 'c'),)  # cases work's specific == ('a', 'b', 'c')
    ])
    def test_validation_invalid_type(self, value):
        field = self.test_field(required=False, nullable=True)
        self.assertEqual(field.error_messages['invalid_type'], "Value type must be a string.")
        with self.assertRaisesRegexp(api.ValidationError, r"Value type must be a string\."):
            field.validate(value)

    @cases([
        '123',
        'String',
        'site.com',
        u'678',
        u'Unicode',
        u'www.ru.ru'
    ])
    def test_validation_invalid_value(self, value):
        field = self.test_field(required=False, nullable=True)
        self.assertEqual(field.error_messages['invalid_value'], "Value must contain @ symbol.")
        with self.assertRaisesRegexp(api.ValidationError, r"Value must contain @ symbol\."):
            field.validate(value)

class TestPhoneField(unittest.TestCase):
    def setUp(self):
        self.test_field = api.PhoneField

    @cases([
        None,
        79998887766,
        70000000000,
        '78123336666',
        u'71234567890',
    ])
    def test_validation_correct_value(self, value):
        field = self.test_field(required=False, nullable=True)
        self.assertTrue(field.validate(value))

    @cases([
        {},
        {'key': 'value'},
        [],
        [9, 8, 7, 6, 5],
        ((),),
        (('a', 'b', 'c'),)  # cases work's specific == ('a', 'b', 'c')
    ])
    def test_validation_invalid_type(self, value):
        field = self.test_field(required=False, nullable=True)
        msg = "Value type must be a string or a number(integer)."
        regex_msg = r"Value type must be a string or a number\(integer\)\."

        self.assertEqual(field.error_messages['invalid_type'], msg)
        with self.assertRaisesRegexp(api.ValidationError, regex_msg):
            field.validate(value)


    @cases([
        19998887766,
        90000000000,
        '08123336666',
        '68123336666',
        u'51234567890',
    ])
    def test_validation_invalid_value(self, value):
        field = self.test_field(required=False, nullable=True)
        msg = "Value must start with 7."
        regex_msg = r"Value must start with 7\."

        self.assertEqual(field.error_messages['invalid_value'], msg)
        with self.assertRaisesRegexp(api.ValidationError, regex_msg):
            field.validate(value)

    @cases([
        7766,
        7000000000,
        7911911911911,
        '7812333',
        '768123336666',
        u'7751234567890',
        u'7',
    ])
    def test_validation_invalid_length(self, value):
        field = self.test_field(required=False, nullable=True)
        msg = "Length of value must be 11 characters."
        regex_msg = r"Length of value must be 11 characters\."

        self.assertEqual(field.error_messages['invalid_length'], msg)
        with self.assertRaisesRegexp(api.ValidationError, regex_msg):
            field.validate(value)

    @cases([
        '781233___66',
        '7.812333666',
        u'7xaq1233366',
        u'7-1-3-3-666',
    ])
    def test_validation_invalid_char(self, value):
        field = self.test_field(required=False, nullable=True)
        msg = "String must contain only characters of numbers."
        regex_msg = r"String must contain only characters of numbers\."

        self.assertEqual(field.error_messages['invalid_char'], msg)
        with self.assertRaisesRegexp(api.ValidationError, regex_msg):
            field.validate(value)

class TestDateField(unittest.TestCase):
    def setUp(self):
        self.test_field = api.DateField

    @cases([
        "10.10.2000",
        "01.12.1900",
        "05.05.1000",
        "07.11.2105",
        "01.01.2001"
    ])
    def test_to_date(self, value):
        field = self.test_field(required=False, nullable=True)
        date = datetime.strptime(value, '%d.%m.%Y')
        self.assertEqual(field._to_date(value), date)

    @cases([
        None,
        "10.10.2000",
        "01.12.1900",
        "05.05.1000",
        "07.11.2105"
    ])
    def test_validation_correct_value(self, value):
        field = self.test_field(required=False, nullable=True)
        self.assertTrue(field.validate(value))

    @cases([
        123,
        50.0,
        {},
        {'key': 'value'},
        [],
        [9, 8, 7, 6, 5],
        ((),),
        (('a', 'b', 'c'),)  # cases work's specific == ('a', 'b', 'c')
    ])
    def test_validation_invalid_type(self, value):
        field = self.test_field(required=False, nullable=True)
        self.assertEqual(field.error_messages['invalid_type'], "Value type must be a string.")
        with self.assertRaisesRegexp(api.ValidationError, r"Value type must be a string\."):
            field.validate(value)

    @cases([
        '1990.01.01',
        '05-06-2001',
        'aa.bb.cccc',
        u'7.6.2011',
        u'1995-3-4'
        u'02.O5.2000'
    ])
    def test_validation_invalid_format(self, value):
        field = self.test_field(required=False, nullable=True)
        msg = "Value format must be DD.MM.YYYY"
        regex_msg = r"Value format must be DD\.MM\.YYYY"

        self.assertEqual(field.error_messages['invalid_format'], msg)
        with self.assertRaisesRegexp(api.ValidationError, regex_msg):
            field.validate(value)

    @cases([
        '00.00.0000',
        '13.13.2013',
        '32.01.1999',
        u'07.06.0000',
        u'66.66.6666',
    ])
    def test_validation_invalid_date(self, value):
        field = self.test_field(required=False, nullable=True)
        msg = "Value must be valid date."
        regex_msg = r"Value must be valid date\."

        self.assertEqual(field.error_messages['invalid_date'], msg)
        with self.assertRaisesRegexp(api.ValidationError, regex_msg):
            field.validate(value)

    @cases([
        "10.10.2000",
        "01.12.1900",
        "05.05.1000",
        "07.11.2105"
    ])
    def test_clean_data_to_datetime(self, value):
        field = self.test_field(required=False, nullable=True)
        self.assertIsInstance(field.clean(value), datetime)


class TestBirthDayField(unittest.TestCase):
    def setUp(self):
        self.test_field = api.BirthDayField

    @cases([
        None,
        datetime.now().replace(year=datetime.now().year - 10).strftime('%d.%m.%Y'),
    ])
    def test_validation_correct_value(self, value):
        field = self.test_field(required=False, nullable=True)
        self.assertTrue(field.validate(value))

    @cases([
        datetime.now().replace(year=datetime.now().year + 1).strftime('%d.%m.%Y'),
        '01.01.5000',
        u'07.06.3000',
        u'16.12.6666',
    ])
    def test_validation_future_date(self, value):
        field = self.test_field(required=False, nullable=True)
        msg = "Date mustn't be in the future."
        regex_msg = r"Date mustn't be in the future\."

        self.assertEqual(field.error_messages['future_date'], msg)
        with self.assertRaisesRegexp(api.ValidationError, regex_msg):
            field.validate(value)

    @cases([
        datetime.now().replace(year=datetime.now().year - 70).strftime('%d.%m.%Y'),
        '01.01.1800',
        '13.12.0001',
        '30.01.1948',
        u'07.06.1900',
        u'16.12.1604',
    ])
    def test_validation_invalid_year(self, value):
        field = self.test_field(required=False, nullable=True)
        msg = "Age must be less than 70 years."
        regex_msg = r"Age must be less than 70 years\."

        self.assertEqual(field.error_messages['invalid_year'], msg)
        with self.assertRaisesRegexp(api.ValidationError, regex_msg):
            field.validate(value)


class TestGenderField(unittest.TestCase):
    def setUp(self):
        self.test_field = api.GenderField

    @cases([
        None,
        0,
        1,
        2
    ])
    def test_validation_correct_value(self, value):
        field = self.test_field(required=False, nullable=True)
        self.assertTrue(field.validate(value))

    @cases([
        -1,
        5,
        10,
        '1',
        u'0',
    ])
    def test_validation_invalid_value(self, value):
        field = self.test_field(required=False, nullable=True)
        msg = "Value must be 0, 1 or 2."
        regex_msg = r"Value must be 0, 1 or 2\."

        self.assertEqual(field.error_messages['invalid_value'], msg)
        with self.assertRaisesRegexp(api.ValidationError, regex_msg):
            field.validate(value)

    @cases([
        0,
        1.0,
        1,
        100,
        99999
    ])
    def test_clean_data_to_int(self, value):
        field = self.test_field(required=False, nullable=True)
        self.assertIsInstance(field.clean(value), int)

class TestClientIDsField(unittest.TestCase):
    def setUp(self):
        self.test_field = api.ClientIDsField

    @cases([
        None,
        [],
        [1, 2, 3],
        [0, 5, 10000],
        [9999999, 213, 10]
    ])
    def test_validation_correct_value(self, value):
        field = self.test_field(required=False, nullable=True)
        self.assertTrue(field.validate(value))

    @cases([
        '',
        u'Строка',
        123,
        50.0,
        {},
        {'key': 'value'},
        ((),),
        (('a', 'b', 'c'),)  # cases work's specific == ('a', 'b', 'c')
    ])
    def test_validation_invalid_type(self, value):
        field = self.test_field(required=False, nullable=True)
        msg = "Value type must be an array."
        regex_msg = r"Value type must be an array\."

        self.assertEqual(field.error_messages['invalid_type'], msg)
        with self.assertRaisesRegexp(api.ValidationError, regex_msg):
            field.validate(value)

    @cases([
        [-1],
        [0, 3, -10],
        [12.0, 10, 6],
        ['a', 'b', 'c'],
        [u'А', u'б', u'с'],
    ])
    def test_validation_invalid_value(self, value):
        field = self.test_field(required=False, nullable=True)
        msg = "Type of elements of list must be a positive number(integer)."
        regex_msg = r"Type of elements of list must be a positive number\(integer\)\."

        self.assertEqual(field.error_messages['invalid_value'], msg)
        with self.assertRaisesRegexp(api.ValidationError, regex_msg):
            field.validate(value)

    @cases([
        None,
        [],
        [1, 2, 3],
        [0, 5, 10000],
        [9999999, 213, 10]
    ])
    def test_clean_data_to_list(self, value):
        field = self.test_field(required=False, nullable=True)
        self.assertIsInstance(field.clean(value), list)


if __name__ == '__main__':
    unittest.main()
