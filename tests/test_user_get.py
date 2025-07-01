import json
import urllib.request
import time
import hashlib

# REQUEST CODE FOR PHONE NUMBER

print('Supplying phone number for verification')
post_url = 'http://localhost:8080/v1/user/phone/register'
data = {
  'phone_number': '+15128675309',
}

params = json.dumps(data).encode('utf8')
req = urllib.request.Request(
  post_url,
  data=params,
  headers={'content-type': 'application/json'}
)
response = urllib.request.urlopen(req)

code = input('Code sent to phone number: ')

# VERIFY PHONE NUMBER

print('Verifying code')
post_url = 'http://localhost:8080/v1/user/phone/verify'
data = {
  'phone_number': '+15128675309',
  'verification_code': code,
}

params = json.dumps(data).encode('utf8')
req = urllib.request.Request(
  post_url,
  data=params,
  headers={'content-type': 'application/json'}
)
response_json = urllib.request.urlopen(req).read()
response = json.loads(response_json)

code_auth_token = response['auth_token']


# LOGIN
print('Logging in')
post_url = 'http://localhost:8080/v1/user/login'
data = {
  'phone_number': '+15128675309',
  'password': 'some_password_123',
}
headers = {
  'content-type': 'application/json',
  'Authorization': 'bearer %s' % code_auth_token,
}
params = json.dumps(data).encode('utf8')
req = urllib.request.Request(
  post_url,
  data=params,
  headers=headers,
)
response_json = urllib.request.urlopen(req).read()
print(response_json)
response = json.loads(response_json)

auth_token = response['auth_token']

# USER GET

post_url = 'http://localhost:8080/v1/user/get'
data = {
  'user_ids': ['u:ebbbb0bd-522a-4206-8245-7e3fcbc43029'],
}
headers = {
  'content-type': 'application/json',
  'Authorization': 'bearer %s' % auth_token,
}

params = json.dumps(data).encode('utf8')
req = urllib.request.Request(
  post_url,
  data=params,
  headers=headers,
)
response = urllib.request.urlopen(req)

print('Response: %s' % json.loads(response.read()))
