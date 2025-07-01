import datetime
from functools import wraps
import jwt
import os

from flask import jsonify
from flask import request

if os.getenv('AUTH_SECRET_KEY') is None:
  raise Exception('Environment variable AUTH_SECRET_KEY not found. Cannot start')

class ExpiredAuthException(Exception):
  pass

class InvalidAuthException(Exception):
  pass

def encode_auth_token(user_id, duration_days=30):
  """
  Generates an auth token
  :return: string
  """
  payload = {
    'exp': datetime.datetime.utcnow() + datetime.timedelta(duration_days),
    'iat': datetime.datetime.utcnow(),
    'sub': user_id,
  }
  return jwt.encode(
    payload,
    os.getenv('AUTH_SECRET_KEY'),
    algorithm='HS256'
  )

def decode_auth_token(auth_token):
  """
  Decodes the auth token
  :param auth_token:
  :return: user_id
  """
  try:
    payload = jwt.decode(auth_token, os.getenv('AUTH_SECRET_KEY'), algorithms=["HS256"])
    return payload['sub']
  except jwt.ExpiredSignatureError:
    raise ExpiredAuthException()
  except jwt.InvalidTokenError:
    raise InvalidAuthException()

def _get_auth_token(content):
  auth_token = None

  # First see if we can get a token from the headers
  auth_header = request.headers.get("Authorization", None)
  if auth_header is not None:
    parts = auth_header.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
      auth_token = parts[1]

  return auth_token

def ensure_user_authenticated(func): 
  @wraps(func)
  def inner(*args, **kwargs): 
    content = request.get_json()
    if content is None:
      return jsonify({"status": "failure", "failure_code": "NOT_LOGGED_IN", "failure_reason": "content is null"})

    auth_token = _get_auth_token(content)
    if auth_token is None:
      print("auth_token is null")
      return jsonify({"status": "failure", "failure_code": "NOT_LOGGED_IN", "failure_reason": "auth_token is null"})
    try:
      my_user_id = decode_auth_token(auth_token)
    except ExpiredAuthException:
      print("auth_token expired")
      return jsonify({"status": "failure", "failure_code": "NOT_LOGGED_IN", "failure_reason": "auth_token expired"})
    except InvalidAuthException as e:
      print("auth_token invalid %s" % (e))
      return jsonify({"status": "failure", "failure_code": "NOT_LOGGED_IN", "failure_reason": "auth_token invalid"})

    # calling the actual function now 
    # inside the wrapper function. 
    return func(my_user_id, *args, **kwargs)

  return inner

def check_if_user_authenticated(func): 
  @wraps(func)
  def inner(*args, **kwargs):
    content = None
    # Check if there is json content in the request
    if request.data is not None and len(request.data) > 0:
      content = request.get_json()
    auth_token = _get_auth_token(content)
    my_user_id = None
    if auth_token is not None:
      try:
        my_user_id = decode_auth_token(auth_token)
      except ExpiredAuthException:
        pass
      except InvalidAuthException:
        pass

    kwargs['my_user_id'] = my_user_id
    return func(*args, **kwargs)

  return inner
