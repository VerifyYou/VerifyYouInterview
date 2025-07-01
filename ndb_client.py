import os
from google.cloud import ndb

client = ndb.Client(project=os.getenv('PROJECT_ID'), database='default')
