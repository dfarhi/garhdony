path = "/home/django/forkbomb-3.0-master/" ##Trailing slash is important.
DEBUG = True
SENDFILE_BACKEND = 'sendfile.backends.nginx'
DO_LOGGING = True  # Do we log all the debug prints or not?

SENDFILE_ROOT = "/home/django/forkbomb-3.0-master/media"
SENDFILE_URL = "/media"
