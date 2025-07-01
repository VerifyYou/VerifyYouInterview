import json
import urllib.request
import time
import hashlib

post_url = 'http://localhost:8080/v1/user/create'
data = {
  'phone_number': '+15128675309',
  'password': 'some_password_123',
}
headers = {
  'content-type': 'application/json',
  'Authorization': 'bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NTEzNzc1NjQsImlhdCI6MTc1MTM0MzAwNCwic3ViIjoidmM6MWQxNGM1N2UtODE5NC00ODhkLWFmMTUtMGE5MzI4NzQ1ZmU1In0.LmVj-AkdLTgVJ-tElxM5JoP4cGcbjJapfJtJO_ubY9k',
}

params = json.dumps(data).encode('utf8')
req = urllib.request.Request(
  post_url,
  data=params,
  headers=headers,
)
response = urllib.request.urlopen(req)

print("Response: %s" % response.read())
