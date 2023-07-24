# Django settings for dogmas project.

DATABASES = {
    'default': {
#        'ENGINE': 'django.db.backends.sqlite3',
#        'NAME': path + 'garhdony.db',
#	'USER': '',
#	'PASSWORD': '',
#	'HOST': '',
#        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.

	'ENGINE': 'django.db.backends.mysql',
	'NAME': 'forkbomb',
	'USER': 'forkbomb',
	'PASSWORD': '5stsav67TEz86NYK',
	'HOST': 'localhost'
    }
}


