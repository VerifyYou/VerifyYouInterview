import os
import time
from protorpc import messages
from google.cloud import ndb
from flask import jsonify

from config import MINIMUM_USER_UPDATE_TIMESTAMP_S

from ndb_client import client

class UserType(messages.Enum):
    INDIVIDUAL = 1
    COMPANY = 2
    GROUP = 3


class User(ndb.Model):
    # Key = user_id
    name = ndb.StringProperty()
    phone_number = ndb.StringProperty() #to be stored +12345678910
    encrypted_password = ndb.StringProperty()

    type = ndb.IntegerProperty(required=True)

    create_timestamp_s = ndb.FloatProperty()
    update_timestamp_s = ndb.FloatProperty()
    deleted_timestamp_s = ndb.FloatProperty()

    deleted = ndb.BooleanProperty()
    deleted_reason = ndb.StringProperty()

def get_user_objects_from_users(my_user_id, users, remove_deleted=True):
    returned_users = {}
    for user in users:
        if user is None:
            continue

        if user.deleted and remove_deleted:
            continue

        if user.type == int(UserType.INDIVIDUAL):
            user_type = "INDIVIDUAL"
        elif user.type == int(UserType.COMPANY):
            user_type = "COMPANY"
        elif user.type == int(UserType.GROUP):
            user_type = "GROUP"
        else:
            print("ERROR: User with id %s had unknown type: %s" % (user.key.id(), user.type))
            user_type = "UNKNOWN"

        returned_users[user.key.id()] = {
            "name": user.name,
            "type": user_type,
            "deleted": user.deleted,
            "update_timestamp_s": max(user.update_timestamp_s, MINIMUM_USER_UPDATE_TIMESTAMP_S),
        }

        # Higher permissions allow for the following fields:
        if my_user_id is not None and user.key.id() == my_user_id:
            returned_users[user.key.id()].update({
                "phone_number": user.phone_number,
            })

    return returned_users


def get_user_objects_from_user_ids(my_user_id, user_ids, remove_deleted=True):
    with client.context():
        keys = [ndb.Key(User, user_id) for user_id in user_ids]
        users = ndb.get_multi(keys)
    return get_user_objects_from_users(my_user_id, users, remove_deleted)

@ndb.transactional()
def edit_user(user_id, name=None):

    key = ndb.Key(User, user_id)
    user = key.get()

    if user is None or user.deleted:
        return jsonify({"status": "failure", "failure_code": "DOES_NOT_EXIST"})
    
    if name is not None:
        user.name = name

    # Update update_timestamp_s. If the time of the server is behind the time of the user,
    # just bump the update timestamp forward 1 second.
    user.update_timestamp_s = max(int(time.time()), user.update_timestamp_s+1)

    # Store down
    user.put()

    return jsonify({
        "status": "success",
        "update_timestamp_s": user.update_timestamp_s,
    })
