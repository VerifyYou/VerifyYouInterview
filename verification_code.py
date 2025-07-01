import time
from uuid import uuid4
import secrets

from google.cloud import ndb

from config import VERIFICATION_CODE_LIFETIME_S, VERIFICATION_CODE_LENGTH

from user_model import User
from verification_code_model import VerificationCode

def generate_random_code(size):
    new_code = ''
    for i in range(size):
        new_code += str(secrets.randbelow(10))
    return new_code


def _deactivate_code(verification_code):
    """Helper function meant to be called with `client.context()` inside `ndb.transactional` protection"""
    verification_code.valid = False
    verification_code.put()

class PhoneNumberAlreadyRegisteredException(Exception):
    pass

@ndb.transactional()
def _create_code(number, code):
    # Check for any pre-existing codes to deactivate
    existing_codes = VerificationCode.query(
        VerificationCode.phone_number == number
    )

    for existing_code in existing_codes:
        # Deactivate code if still valid
        if existing_code.valid:
            _deactivate_code(existing_code)

    code_id = 'vc:'+str(uuid4())
    key = ndb.Key(VerificationCode, code_id) 

    entity = VerificationCode(
        key=key,
        phone_number=number,
        valid=True,
        code=code,
        create_timestamp_s=int(time.time()),
        expiration_timestamp_s=int(time.time()) + VERIFICATION_CODE_LIFETIME_S,
    )
    entity.put()
    return entity


def send_message(phone_number, message):
    # Simulate sending a message via an external service
    print(f"Pretending to send message to {phone_number}: {message}")

def create_and_send_verification_code(phone_number):
    code = generate_random_code(VERIFICATION_CODE_LENGTH)

    # Create in database
    new_verification_code = _create_code(
        phone_number,
        code,
    )

    if new_verification_code is None:
        return None

    try:
        message = send_message(phone_number, "Your VerifyYou verification code is: " + new_verification_code.code)
    except RuntimeError as ex:
        message = "Could not send message: " + str(ex)
    except Exception as e:
        message = "Did not send message: " + str(e)
    
    return {
        'id': new_verification_code.key.id(),
        'number': new_verification_code.phone_number,
        'code': new_verification_code.code,
        'message': message
    }

@ndb.transactional()
def check_verification_code(number, code):
    """Checks if code matches a valid code for given phone number"""
    #retrieve all codes for this user
    existing_codes = VerificationCode.query(
            VerificationCode.phone_number == number
    )

    current_time=int(time.time())
    for verification_code in existing_codes:
        if not verification_code.valid:
            print('Skipping code %s of type %s because it is not valid' % (verification_code.code, type(verification_code.code)))
            continue
        if verification_code.expiration_timestamp_s < current_time:
            print('Skipping code %s of type %s because it has expired' % (verification_code.code, type(verification_code.code)))
            continue
        if verification_code.code == code:
            print('Comparing code %s of type %s with code %s of type %s' % (verification_code.code, type(verification_code.code), code, type(code)))
            return verification_code
    
    return None





