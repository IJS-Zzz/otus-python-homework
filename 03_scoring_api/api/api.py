#!/usr/bin/env python
# -*- coding: utf-8 -*-


import copy
import datetime
import hashlib
import json
import logging
import re
import uuid
from abc import ABCMeta, abstractmethod
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from collections import OrderedDict
from optparse import OptionParser

import scoring
from store import RedisConnection, Storage


SALT = "Otus"
ADMIN_LOGIN = "admin"
ADMIN_SALT = "42"

STORE_CONFIG = {
    'host': 'localhost',
    'port': 6379,
    'db': 0,
    'password': None,
    'timeout': 3,
    'retry': 3,
    'backoff_factor': 0.1,
}

OK = 200
BAD_REQUEST = 400
FORBIDDEN = 403
NOT_FOUND = 404
INVALID_REQUEST = 422
INTERNAL_ERROR = 500
ERRORS = {
    BAD_REQUEST: "Bad Request",
    FORBIDDEN: "Forbidden",
    NOT_FOUND: "Not Found",
    INVALID_REQUEST: "Invalid Request",
    INTERNAL_ERROR: "Internal Server Error",
}
UNKNOWN = 0
MALE = 1
FEMALE = 2
GENDERS = {
    UNKNOWN: "unknown",
    MALE: "male",
    FEMALE: "female",
}


class ValidationError(Exception):
    pass


##### Fields #####

class Field(object):
    """
        Base class for other fields
    """
    __metaclass__ = ABCMeta
    empty_values = (None, '', [], (), {})

    def __init__(self, required=True, nullable=False):
        self.error_messages = {
            'required': "This field is required.",
            'nullable': "This field can't be empty.",
        }
        self.required = required
        self.nullable = nullable

        # does field exist in request?
        self.is_exist = False

    def is_empty(self, value):
        return value in self.empty_values

    def check_required_and_nullable(self, value):
        # Check for required
        if not self.is_exist and self.required:
            raise ValidationError(self.error_messages['required'])

        # Check for nullable
        if not self.nullable and self.is_empty(value):
            raise ValidationError(self.error_messages['nullable'])

    def validate(self, value):
        self.check_required_and_nullable(value)
        if value is not None:
            self.field_validate(value)
        return True

    @abstractmethod
    def field_validate(self, value):
        """
            Validation logic:
            If value isn't valid - raise ValidationError('error message')
        """
        raise NotImplementedError

    @abstractmethod
    def clean(self, value):
        """
            Clean data with field rules
            :param  value (raw data)
            :return value (clean data)
        """
        raise NotImplementedError


class CharField(Field):
    """
        Character field:
        1. type - str (unicode)
    """
    def __init__(self, *args, **kwarg):
        super(CharField, self).__init__(*args, **kwarg)
        self.error_messages.update({
            'invalid_type': "Value type must be a string.",
        })

    def field_validate(self, value):
        if not isinstance(value, (str, unicode)):
            raise ValidationError(self.error_messages['invalid_type'])

    def clean(self, value):
        """ Convert value to unicode """
        if self.is_empty(value):
            return u''
        if isinstance(value, unicode):
            return value
        if isinstance(value, str):
            return value.decode('utf8')
        return unicode(value)


class ArgumentsField(Field):
    """
        Arguments field:
        1. type - dict (JSON Object)
    """
    def __init__(self, *args, **kwarg):
        super(ArgumentsField, self).__init__(*args, **kwarg)
        self.error_messages.update({
            'invalid_type': "Value type must be JSON object.",
        })

    def field_validate(self, value):
        if not isinstance(value, dict):
            raise ValidationError(self.error_messages['invalid_type'])

    def clean(self, value):
        """ Convert value to dict """
        if self.is_empty(value):
            return {}
        if isinstance(value, dict):
            return value
        return dict(value)


class EmailField(CharField):
    """
        Email field:
        1. type - str
        2. must contain '@' char
    """
    def __init__(self, *args, **kwarg):
        super(EmailField, self).__init__(*args, **kwarg)
        self.error_messages.update({
            'invalid_value': "Value must contain @ symbol.",
        })

    def field_validate(self, value):
        super(EmailField, self).field_validate(value)
        if self.is_empty(value):
            return
        if '@' not in value:
            raise ValidationError(self.error_messages['invalid_value'])


class PhoneField(CharField):
    """
        Phone field:
        1. type - str or int
        2. length = 11
        3. field[0] = 7
    """
    def __init__(self, *args, **kwarg):
        super(PhoneField, self).__init__(*args, **kwarg)
        self.conditions = {
            'length': 11,
            'first_char': 7
        }
        self.error_messages.update({
            'invalid_type': "Value type must be a string or a number(integer).",
            'invalid_value': "Value must start with 7.",
            'invalid_length': "Length of value must be 11 characters.",
            'invalid_char': "String must contain only characters of numbers."
        })
    
    def field_validate(self, value):
        if not isinstance(value, (str, unicode, int)):
            raise ValidationError(self.error_messages['invalid_type'])
        if self.is_empty(value):
            return

        value_str = unicode(value)
        if len(value_str) != self.conditions['length']:
            raise ValidationError(self.error_messages['invalid_length'])

        if not value_str.startswith(unicode(self.conditions['first_char'])):
            raise ValidationError(self.error_messages['invalid_value'])

        if isinstance(value, (str, unicode)):
            for c in value:
                try:
                    int(c)
                except ValueError as e:
                    raise ValidationError(self.error_messages['invalid_char'])


class DateField(CharField):
    """
        Date field:
        1. type - str
        2. format - DD.MM.YYYY
    """
    def __init__(self, *args, **kwarg):
        super(DateField, self).__init__(*args, **kwarg)
        self.error_messages.update({
            'invalid_format': "Value format must be DD.MM.YYYY",
            'invalid_date': "Value must be valid date.",
        })

    def _to_date(self, value):
        return datetime.datetime.strptime(value, '%d.%m.%Y')

    def field_validate(self, value):
        super(DateField, self).field_validate(value)
        if self.is_empty(value):
            return

        if not re.match(r'\d{2}\.\d{2}\.\d{4}$', value):
            raise ValidationError(self.error_messages['invalid_format'])

        try:
            self._to_date(value)
        except (TypeError, ValueError):
            raise ValidationError(self.error_messages['invalid_date'])

    def clean(self, value):
        """ Convert value to datetime object or None"""
        if self.is_empty(value):
            return
        return self._to_date(value)


class BirthDayField(DateField):
    """
        Date field:
        1. type - str
        2. format - DD.MM.YYYY
        3. Age < 70
    """
    def __init__(self, *args, **kwarg):
        super(BirthDayField, self).__init__(*args, **kwarg)
        self.conditions = {
            'max_age': 70,
        }
        self.error_messages.update({
            'future_date': "Date mustn't be in the future.",
            'invalid_year': "Age must be less than 70 years.",
        })

    def field_validate(self, value):
        super(BirthDayField, self).field_validate(value)
        if self.is_empty(value):
            return

        now = datetime.datetime.now()
        birth_date = self._to_date(value)
        if birth_date > now:
            raise ValidationError(self.error_messages['future_date'])

        past = now.replace(year=(now.year - self.conditions['max_age']))
        if birth_date < past:
            raise ValidationError(self.error_messages['invalid_year'])


class GenderField(Field):
    """
        Gender field:
        1. type - int
        2. value in [0, 1, 2]
    """
    def __init__(self, *args, **kwarg):
        super(GenderField, self).__init__(*args, **kwarg)
        self.error_messages.update({
            'invalid_value': "Value must be {}, {} or {}.".format(*GENDERS)
        })

    def field_validate(self, value):
        if self.is_empty(value):
            return

        if value not in GENDERS:
            raise ValidationError(self.error_messages['invalid_value'])

    def clean(self, value):
        if self.is_empty(value):
            return
        if not isinstance(value, int):
            return int(value)
        return value


class ClientIDsField(Field):
    """
        Client ID's:
        1. type - list
        2. length > 0
        3. type of elements of list - int
    """
    def __init__(self, *args, **kwarg):
        super(ClientIDsField, self).__init__(*args, **kwarg)
        self.error_messages.update({
            'invalid_type': "Value type must be an array.",
            'invalid_value': "Type of elements of list must be a positive number(integer)."
        })

    def field_validate(self, value):
        if not isinstance(value, list):
            raise ValidationError(self.error_messages['invalid_type'])

        for elem in value:
            if not isinstance(elem, int) or elem < 0:
                raise ValidationError(self.error_messages['invalid_value'])

    def clean(self, value):
        if self.is_empty(value):
            return []
        return value


##### Requests #####

class DeclarativeFieldsMetaclass(type):
    """
        Metaclass that collects Fields declared on the base classes.
    """
    def __new__(cls, name, bases, attrs):
        # Collect fields from current class.
        current_fields = []
        for key, value in list(attrs.items()):
            if isinstance(value, Field):
                current_fields.append((key, value))
                attrs.pop(key)
        attrs['declared_fields'] = OrderedDict(current_fields)

        new_class = (super(DeclarativeFieldsMetaclass, cls)
            .__new__(cls, name, bases, attrs))

        # Walk through the MRO.
        declared_fields = OrderedDict()
        for base in reversed(new_class.__mro__):
            # Collect fields from base class.
            if hasattr(base, 'declared_fields'):
                declared_fields.update(base.declared_fields)

            # Field shadowing.
            for attr, value in base.__dict__.items():
                if value is None and attr in declared_fields:
                    declared_fields.pop(attr)

        new_class.base_fields = declared_fields
        new_class.declared_fields = declared_fields

        return new_class


class BaseRequest(object):
    """
        BaseRequest
    """
    __metaclass__ = DeclarativeFieldsMetaclass

    def __init__(self, data=None):
        """
            Request init.
            Copies declarative classes to self.fields_classes
            and deletes them from attributes

            :param data: dict
        """
        if not hasattr(self, 'error_messages'):
            self.error_messages = {}
        self.error_messages.update({
            'unexpected': "Field is unexpected",
        })

        self.fields = copy.deepcopy(self.base_fields)

        self.data = {} if data is None else data
        self.cleaned_data = {}

        self._errors = None


    @property
    def errors(self):
        """
            Return a dict of errors for the data provided for validation.
        """
        if self._errors is None:
            self.full_clean()
        return self._errors

    def is_valid(self):
        """
            Return True if there has no errors, or False otherwise.
        """
        return not self.errors

    def full_clean(self):
        """
            Clean all of self.data and populate self._errors and self.cleaned_data.
        """
        # Init error dict
        self._errors = {}

        # Check to unexpected fields
        for field_name in self.data.keys():
            if field_name not in self.fields:
                self._errors[field_name] = self.error_messages['unexpected']

        self._validate()
        self._clean()
        self.validate()

    def validate(self):
        """
            Validation method for redefine in children classes.
        """
        pass

    def _validate(self):
        """
            Fields validation method.
            Checks required and nullable fields and validate
            their values.
        """
        for field_name, field_cls in self.fields.items():
            # Check that field is exist in request.
            field_cls.is_exist = field_name in self.data

            # Validate field value
            field_value = self.data.get(field_name)
            try:
                field_cls.validate(field_value)
            except ValidationError as e:
                self._errors[field_name] = str(e)

    def _clean(self):
        """
            Clean data and save them in self.cleaned_data.
            Add non-empty fields in self.filled_fields.
        """
        if self._errors:
            return

        for field_name, field_cls in self.fields.items():
            field_value = self.data.get(field_name)
            clean_value = field_cls.clean(field_value)
            self.cleaned_data[field_name] = clean_value

    def __getattr__(self, value):
        """
            Return fields value from self.cleaned_data like class attribute.
        """
        try:
            return object.__getattribute__(self, value)
        except AttributeError:
            if value in object.__getattribute__(self, 'cleaned_data'):
                return object.__getattribute__(self, 'cleaned_data')[value]
            raise AttributeError(
                "'{}' object has no attribute '{}'".format(
                    object.__getattribute__(self, '__class__').__name__, value
                )
            )


class ClientsInterestsRequest(BaseRequest):
    """
        Handler for method clients_interests
    """
    client_ids = ClientIDsField(required=True)
    date = DateField(required=False, nullable=True)

    def get_answer(self, store, context, is_admin):
        """
            Return user's interests for list of ids
        """
        context['nclients'] = len(self.client_ids)
        result = {}
        for client_id in self.client_ids:
            result[client_id] = scoring.get_interests(store, client_id)

        return result


class OnlineScoreRequest(BaseRequest):
    """
        Handler for method online_score
    """
    first_name = CharField(required=False, nullable=True)
    last_name = CharField(required=False, nullable=True)
    email = EmailField(required=False, nullable=True)
    phone = PhoneField(required=False, nullable=True)
    birthday = BirthDayField(required=False, nullable=True)
    gender = GenderField(required=False, nullable=True)

    def __init__(self, *args, **kwargs):
        self.field_pairs = [
            ("phone", "email"),
            ("first_name", "last_name"),
            ("gender", "birthday")
        ]
        pairs_str = ", ".join(["(%s, %s)" % pair for pair in self.field_pairs])

        if not hasattr(self, 'error_messages'):
            self.error_messages = {}
        self.error_messages.update({
            "invalid_pairs": "Request must have at least one pair "
                             "with non-empty values of: {}".format(pairs_str)
        })

        super(OnlineScoreRequest, self).__init__(*args, **kwargs)

    def validate(self):
        """
            Added extra validation.
            Checks that at least one pair of fields is non-empty of:
                phone - email
                first_name - last_name
                gender - birthday
        """
        not_valid = True

        for member_1, member_2 in self.field_pairs:
            if hasattr(self, member_1) and hasattr(self, member_2):

                # check first member of pair
                if self.fields[member_1].is_empty(getattr(self, member_1)):
                    continue

                # check second member of pair
                if self.fields[member_2].is_empty(getattr(self, member_2)):
                    continue

                # both fields in pair isn't empty
                not_valid = False
                break

        if not_valid:
            self._errors["invalid_pairs"] = self.error_messages["invalid_pairs"]

    def get_answer(self, store, context, is_admin):
        """
            Return user's score, calculated by given fields
        """
        # context["has"] = [fields_name for fields_name in self.filled_fields]
        context["has"] = [fields_name for fields_name, field_cls in self.fields.items() if field_cls.is_exist]

        if is_admin:
            result = 42
        else:
            result = scoring.get_score(store,
                                       phone=self.phone,
                                       email=self.email,
                                       birthday=self.birthday,
                                       gender=self.gender,
                                       first_name=self.first_name,
                                       last_name=self.last_name)
        return {"score": result}


class MethodRequest(BaseRequest):
    """
        Handler for validation top-level request args
    """
    account = CharField(required=False, nullable=True)
    login = CharField(required=True, nullable=True)
    token = CharField(required=True, nullable=True)
    method = CharField(required=True, nullable=False)
    arguments = ArgumentsField(required=True, nullable=True)

    @property
    def is_admin(self):
        return self.login == ADMIN_LOGIN


def check_auth(request):
    """
        Check user authorization
    """
    if request.is_admin:
        digest = hashlib.sha512(datetime.datetime.now().strftime("%Y%m%d%H") + ADMIN_SALT).hexdigest()
    else:
        digest = hashlib.sha512(request.account + request.login + SALT).hexdigest()
    if digest == request.token:
        return True
    return False


def method_handler(request, context, store):
    """
        Handle request.
        Validate arguments and return result or error

        :param request: {"body": request (dict), "headers": headers (dict)}
        :param context: dict
        :param store: object
        :return: Answer (errors_dict if error), Code
    """

    handlers = {
        "online_score": OnlineScoreRequest,
        "clients_interests": ClientsInterestsRequest,
    }

    # 1. Validate MethodRequest args
    method_request = MethodRequest(request["body"])
    if method_request.errors:
        return method_request.errors, INVALID_REQUEST

    # 2. Check user authorization
    if not check_auth(method_request):
        return ERRORS[FORBIDDEN], FORBIDDEN

    # 3. Check if method exists
    if method_request.method not in handlers:
        msg = "Method {} isn't specified".format(methodrequest.method)
        return msg, NOT_FOUND

    # 4. Validate handler args
    handler = handlers[method_request.method](method_request.arguments)
    if handler.errors:
        return handler.errors, INVALID_REQUEST

    return handler.get_answer(store, context, method_request.is_admin), OK


class MainHTTPHandler(BaseHTTPRequestHandler):
    router = {
        "method": method_handler
    }
    store = Storage(RedisConnection, STORE_CONFIG)

    def get_request_id(self, headers):
        return headers.get('HTTP_X_REQUEST_ID', uuid.uuid4().hex)

    def do_POST(self):
        response, code = {}, OK
        context = {"request_id": self.get_request_id(self.headers)}
        request = None
        try:
            data_string = self.rfile.read(int(self.headers['Content-Length']))
            print data_string
            request = json.loads(data_string)  # in Unicode
        except:
            code = BAD_REQUEST

        if request:
            path = self.path.strip("/")
            logging.info("%s: %s %s" % (self.path, data_string, context["request_id"]))
            if path in self.router:
                try:
                    response, code = self.router[path]({"body": request, "headers": self.headers}, context, self.store)
                except Exception, e:
                    logging.exception("Unexpected error: %s" % e)
                    code = INTERNAL_ERROR
            else:
                code = NOT_FOUND

        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        if code not in ERRORS:
            r = {"response": response, "code": code}
        else:
            r = {"error": response or ERRORS.get(code, "Unknown Error"), "code": code}
        context.update(r)
        logging.info(context)

        # save correct unicode in response
        response_data = json.dumps(r, sort_keys=True, ensure_ascii=False).encode('utf8')
        self.wfile.write(response_data)
        return


if __name__ == "__main__":
    op = OptionParser()
    op.add_option("-p", "--port", action="store", type=int, default=8080)
    op.add_option("-l", "--log", action="store", default=None)
    (opts, args) = op.parse_args()
    logging.basicConfig(filename=opts.log, level=logging.INFO,
                        format='[%(asctime)s] %(levelname).1s %(message)s', datefmt='%Y.%m.%d %H:%M:%S')
    server = HTTPServer(("localhost", opts.port), MainHTTPHandler)
    logging.info("Starting server at %s" % opts.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()
