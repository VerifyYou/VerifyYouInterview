import json
import urllib.request
import time
import hashlib

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

print("Response: %s" % response.read())
