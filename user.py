import binascii
import os
import time
from uuid import uuid4
import phonenumbers

from flask import Blueprint, jsonify, request
from google.cloud import ndb

from crypt_helper import hash_password, check_password
from helpers import isValidUserId, limit_content_length, returnFailure, returnSuccess, FailureCode
from config import VERIFICATION_CODE_LENGTH

from auth_token import encode_auth_token, ensure_user_authenticated
from user_model import get_user_objects_from_user_ids, User, UserType, edit_user
from verification_code import create_and_send_verification_code, check_verification_code
from verification_code_model import VerificationCode

from ndb_client import client

user_app = Blueprint('user_app', __name__)

# Returns (user, is_new)
@ndb.transactional()
def _create_user(user_id, phone_number, encrypted_password, user_type):
    # Check for any pre-existing accounts that collide with this one
    if user_type == UserType.INDIVIDUAL:
        users = User.query(
            User.phone_number == phone_number,
        )

        for user in users:
            if not user.deleted:
                return (user, False)

    key = ndb.Key(User, user_id)
    entity = User(
        key=key,
        phone_number=phone_number,
        encrypted_password=encrypted_password,
        update_timestamp_s=int(time.time()),
        create_timestamp_s=int(time.time()),
        type=int(user_type),
        deleted=False
    )
    entity.put()

    return (entity, True)

enabled_countries = [
    "US",  # United States
    "CA",  # Canada
    "GB",  # United Kingdom
]

@user_app.route('/v1/user/phone/register', methods=['POST', 'PUT'])
@limit_content_length(4 * 1024 * 1024)
def user_phone_register():
    # Parse json
    content = request.get_json()

    phone = content.get('phone_number')

    if phone is None:
        print('phone must be supplied')
        return returnFailure(FailureCode.INVALID_API_ACCESS, 'phone_number must be supplied')

    if len(phone) > 32:
        print('phone_number is too long')
        return returnFailure(FailureCode.INVALID_API_ACCESS, 'phone number is too long')

    try:
        # Validates and normalizes phone numbers
        parsed_phone = phonenumbers.parse(phone)
        if not phonenumbers.is_possible_number(parsed_phone):
            raise Exception("Supplied number is not a possible phone number")
        if not phonenumbers.is_valid_number(parsed_phone):
            raise Exception("Supplied number is not a valid phone number")
        if phonenumbers.region_code_for_number(parsed_phone) not in enabled_countries:
            return returnFailure(FailureCode.UNSUPPORTED_COUNTRY_CODE, 'phone number is not in a supported country')
        
    except Exception as e:
        print('phone number %s is invalid' % phone)
        print(str(e))
        return returnFailure(FailureCode.INVALID_API_ACCESS, str(e))
    
    normalized_phone = phonenumbers.format_number(parsed_phone, phonenumbers.PhoneNumberFormat.E164)
    with client.context():
        verification_code_response = create_and_send_verification_code(normalized_phone)
    
    if verification_code_response is None:
        return returnFailure(FailureCode.INTERNAL_ERROR, "verification code failed to send")

    return returnSuccess({})

def get_user_by_phone_number(phone_number):
    with client.context():
        users = User.query(
            User.phone_number == phone_number,
        )
        for user in users:
            if not user.deleted:
                return user
        
    return None

@user_app.route('/v1/user/phone/verify', methods=['POST', 'PUT'])
@limit_content_length(4 * 1024 * 1024)
def user_phone_verify():
    # Parse json
    content = request.get_json()

    phone_number = content.get('phone_number')
    code = content.get('verification_code')

    # Clean and validate input
    if code is None:
        return returnFailure(FailureCode.INVALID_API_ACCESS, 'verification code must be supplied')
    if len(code) != VERIFICATION_CODE_LENGTH or not code.isnumeric():
        return returnFailure(FailureCode.INVALID_API_ACCESS, 'invalid verification code')
    
    if phone_number is None:
        print('phone_number must be supplied')
        return returnFailure(FailureCode.INVALID_API_ACCESS, 'phone_number must be supplied')
    if len(phone_number) > 100:
        return returnFailure(FailureCode.INVALID_API_ACCESS, 'phone number is too long')
    
    # Validate verification code
    with client.context():
        valid_verification_code = check_verification_code(phone_number, code)

    if not valid_verification_code:
        print('Invalid verification code ' + code + ' for phone number ' + phone_number)
        return returnFailure(FailureCode.INVALID_CODE, 'invalid verification code')
    
    code_id = valid_verification_code.key.id()
    auth_token = encode_auth_token(code_id, 0.4)

    # check if user exists 
    existing_user = get_user_by_phone_number(phone_number)

    returnValues = {
        "auth_token": auth_token,
    }
    
    if  existing_user is not None:
        returnValues["existing_user_id"] = existing_user.key.id()

    return returnSuccess(returnValues)

def get_user_by_phone_number(phone_number):
    with client.context():
        users = User.query(
            User.phone_number == phone_number,
        )
        for user in users:
            if not user.deleted:
                return user
        
    return None

# TODO: Make me better
def is_password_sufficiently_strong(password):
    if len(password) < 8:
        return False
    return True

@user_app.route('/v1/user/create', methods=['POST', 'PUT'])
@limit_content_length(1 * 1024 * 1024)
@ensure_user_authenticated
def user_create(my_code_id):
    # Parse json
    content = request.get_json()
    phone_number = content.get('phone_number')
    password = content.get('password')

    if password is None:
        return returnFailure(FailureCode.INVALID_API_ACCESS, 'password must be supplied')
    
    if phone_number is None:
        return returnFailure(FailureCode.INVALID_API_ACCESS, 'phone_number must be supplied')
    if len(phone_number) > 100:
        return returnFailure(FailureCode.INVALID_API_ACCESS, 'phone number is too long')
    
    if not is_password_sufficiently_strong(password):
        return returnFailure(FailureCode.INVALID_API_ACCESS, 'password is not strong enough')

    parsed_phone = phonenumbers.parse(phone_number)
    normalized_phone_number = phonenumbers.format_number(parsed_phone, phonenumbers.PhoneNumberFormat.E164)

    #check verification "ticket"
    with client.context():
        vc_key = ndb.Key(VerificationCode, my_code_id) 
        verification_code = vc_key.get()

    if verification_code.phone_number != phone_number:
        return returnFailure(FailureCode.INVALID_API_ACCESS, 'attempting to authenticate the wrong phone number')
    
    user_id = 'u:'+str(uuid4())
    auth_token = encode_auth_token(user_id)
    
    encrypted_password = hash_password(password)

    user_type = UserType.INDIVIDUAL

    # Create in database
    with client.context():
        _create_user(
            user_id,
            normalized_phone_number,
            encrypted_password,
            user_type
        )
    
    return returnSuccess({
        'user_id': user_id,
        'auth_token': auth_token,
        'user_type': user_type.name,
    })


@user_app.route('/v1/user/login', methods=['POST', 'PUT'])
@limit_content_length(1 * 1024 * 1024)
@ensure_user_authenticated
def user_login(my_code_id):
    # Parse json
    content = request.get_json()
    phone_number = content.get('phone_number')
    password = content.get('password')

    if password is None:
        print('password must be supplied')
        return returnFailure(FailureCode.INVALID_API_ACCESS, 'password must be supplied')
    
    if phone_number is None:
        print('phone_number must be supplied')
        return returnFailure(FailureCode.INVALID_API_ACCESS, 'phone_number must be supplied')
    if len(phone_number) > 100:
        return returnFailure(FailureCode.INVALID_API_ACCESS, 'phone number is too long')

    with client.context():
        vc_key = ndb.Key(VerificationCode, my_code_id) 
        verification_code = vc_key.get()

    if verification_code.phone_number != phone_number:
        return returnFailure(FailureCode.INVALID_API_ACCESS, 'attempting to authenticate the wrong phone number')

    user = get_user_by_phone_number(phone_number)
    if user is None:
        return returnFailure(FailureCode.DOES_NOT_EXIST)

    if not check_password(password, user.encrypted_password):
        print('Invalid password')
        return jsonify({'status': 'failure', 'failure_code': 'INVALID_CREDENTIALS', 'failure_reason': 'Invalid password'})

    auth_token = encode_auth_token(user.key.id())
    #TODO: find a way to access and return connection keys on this API call

    return jsonify({
        'status': 'success',
        'user_id': user.key.id(),
        'auth_token': auth_token,
    })

@limit_content_length(10 * 1024)
@user_app.route('/v1/user/get', methods=['POST', 'PUT'])
@ensure_user_authenticated
def user_get(my_user_id):

    # Parse json
    content = request.get_json()

    # Get user info for user_id
    user_ids = content.get('user_ids')

    # Input verification

    if user_ids is None or type(user_ids) != list:
        return jsonify({
            "status": "failure",
            "failure_code": "INVALID_API_ACCESS",
            "failure_reason": "user_ids must be supplied and must be a list",
        })

    for user_id in user_ids:
        if not isValidUserId(user_id):
            return jsonify({
                "status": "failure",
                "failure_code": "INVALID_API_ACCESS",
                "failure_reason": "user_ids must be a list of valid user ids",
            })

    if len(user_ids) > 50:
        return jsonify({
            "status": "failure",
            "failure_code": "INVALID_API_ACCESS",
            "failure_reason": "Can request a max of 50 user_ids at a time",
        })

    returned_users = get_user_objects_from_user_ids(my_user_id, user_ids, remove_deleted=False)

    return jsonify({
        "status": "success",
        "users": returned_users,
    })

@limit_content_length(1 * 1024 * 1024)
@user_app.route('/v1/user/edit', methods=['POST', 'PUT'])
@ensure_user_authenticated
def user_edit(my_user_id):
    # Parse json
    content = request.get_json()

    name = content.get('name')

    if name is not None:
        if len(name) > 64:
            print('name is too long')
            return returnFailure(FailureCode.INVALID_API_ACCESS, 'name is too long')
        
    with client.context():
        return edit_user(my_user_id, name=name)

@ndb.transactional()
def _delete_user(user_id):
    # should be heavily protected
    # get user
    key = ndb.Key(User, user_id)
    user = key.get()

    if user is None:
        return returnFailure(FailureCode.DOES_NOT_EXIST)

    if user.deleted:
        return returnFailure(FailureCode.ALREADY_COMPLETED)

    user.deleted = True
    user.deleted_timestamp_s = int(time.time())
    user.deleted_reason = "USER_REQUESTED_DELETION"

    # Store down
    user.put()

    return returnSuccess({
       "deleted_timestamp_s": user.deleted_timestamp_s,
    })


@limit_content_length(1 * 1024 * 1024)
@user_app.route('/v1/user/delete', methods=['POST', 'PUT'])
@ensure_user_authenticated
def user_delete(my_user_id):
    with client.context():
        return _delete_user(my_user_id)
