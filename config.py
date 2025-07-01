import os

DEBUG = False

AVATAR_SIDE_SIZE_PX = 1024
VERIFICATION_CODE_LIFETIME_S = 60 * 30 #30 minutes
VERIFICATION_CODE_LENGTH = 6

IS_LOCAL = (os.getenv('IS_LOCAL') == 'True')

# Used for forcing a refresh of user data across all clients
MINIMUM_USER_UPDATE_TIMESTAMP_S = 1749428817