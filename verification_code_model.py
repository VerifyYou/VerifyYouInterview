from protorpc import messages
from google.cloud import ndb



class VerificationCode(ndb.Model):
    #telephone id (uuid)
    phone_number = ndb.StringProperty() # stored in format: +12345678910 
    code = ndb.StringProperty() #verification code (current)
    create_timestamp_s = ndb.FloatProperty()
    expiration_timestamp_s = ndb.FloatProperty() #verification code expiration
    valid = ndb.BooleanProperty()
