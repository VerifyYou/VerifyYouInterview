import os
from functools import wraps
from uuid import UUID
from enum import Enum
from flask import request, abort, jsonify
import json
import time
from google.cloud import logging
from config import IS_LOCAL

class FailureCode(Enum): 
    INVALID_API_ACCESS = 'INVALID_API_ACCESS'
    DOES_NOT_EXIST = 'DOES_NOT_EXIST'
    PERMISSION_DENIED = 'PERMISSION_DENIED'
    ALREADY_EXISTS = 'ALREADY_EXISTS'
    INVALID_CODE = 'INVALID_CODE'
    ALREADY_COMPLETED = 'ALREADY_COMPLETED' #used for idempotent actions that have been accomplished
    INTERNAL_ERROR = 'INTERNAL_ERROR'
    INVALID_STATE = 'INVALID_STATE'
    INVALID_CREDENTIALS = 'INVALID_CREDENTIALS'
    NOT_LOGGED_IN = 'NOT_LOGGED_IN'
    RETRIEVAL_FAILED = 'RETRIEVAL_FAILED'
    BAD_USER = 'BAD_USER'
    DATA_TOO_BIG = 'DATA_TOO_BIG'
    INVALID_URL = 'INVALID_URL'
    TRY_AGAIN = 'TRY_AGAIN'
    EXPIRED = 'EXPIRED'
    UNSUPPORTED_COUNTRY_CODE = 'UNSUPPORTED_COUNTRY_CODE'
    
def limit_content_length(max_length):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            cl = request.content_length
            if cl is not None and cl > max_length:
                abort(413)
            return f(*args, **kwargs)
        return wrapper
    return decorator


def isValidUserId(user_id):
    if type(user_id) != str:
        return False

    if user_id[:2] != 'u:':
        return False
    try:
        UUID(user_id[2:], version=4)
    except ValueError:
        return False

    return True

def returnSuccess(data: dict={}):
    """
    method to structure return data in success instance

    :param dict data: return data
    :return: json object
    """
    data['status'] = 'success'
    return jsonify(data)

def returnFailure(code: FailureCode, reason=None):
    """
    method to structure return data in failure instance

    :param code: utility failure code
    :type code: FailureCode
    :param str reason: failure explanation

    :return: json object
    """

    return_data = {'status': 'failure', 'failure_code': code.value}
    if reason is not None:
        return_data['failure_reason'] = reason

    return jsonify(return_data)

def format_name(first_name, last_name):
    first_name = first_name.title()
    last_name = last_name.title()
    name = '%s %s' % (first_name, last_name)
    name.strip()
    return name

def should_not_reach_here(message, data={}):
    logging_client = logging.Client(project=os.getenv('PROJECT_ID'))
    logger = logging_client.logger('backend_should_not_reach_here_log')

    data['timestamp_s'] = time.time()
    data['message'] = message
    logger.log_struct(data, severity='INFO')
    if (IS_LOCAL):
        print('SHOULD NOT REACH HERE: %s' % json.dumps(data, indent=4))

