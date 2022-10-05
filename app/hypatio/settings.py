"""
Django settings for hypatio project.

Generated by 'django-admin startproject' using Django 1.10.1.

For more information on this file, see
https://docs.djangoproject.com/en/1.10/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.10/ref/settings/
"""

import os
import sys
import logging

from os.path import normpath, join, dirname, abspath
from dbmi_client import environment

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.10/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = environment.get_str("SECRET_KEY", required=True)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = environment.get_bool("DJANGO_DEBUG", default=False)

PROJECT = 'hypatio'

ALLOWED_HOSTS = environment.get_list("ALLOWED_HOSTS", required=True)

# Application definition

INSTALLED_APPS = [
    'dal',
    'dal_select2',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'jquery',
    'bootstrap3',
    'contact',
    'manage',
    'django_countries',
    'profile',
    'projects',
    'health_check',
    'raven.contrib.django.raven_compat',
    'bootstrap_datepicker_plus',
    'storages',
    'django_jsonfield_backport',
    'django_q',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'hypatio.middleware.XRobotsTagMiddleware',
]

ROOT_URLCONF = 'hypatio.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            normpath(join(BASE_DIR, 'templates')),
            normpath(join(dirname(dirname(abspath(__file__))), 'assets')),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'hypatio.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.10/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'hypatio',
        'USER': environment.get_str("MYSQL_USERNAME", default='hypatio'),
        'PASSWORD': environment.get_str("MYSQL_PASSWORD", required=True),
        'HOST': environment.get_str("MYSQL_HOST", required=True),
        'PORT': environment.get_str("MYSQL_PORT", '3306'),
    }
}

# Password validation
# https://docs.djangoproject.com/en/1.10/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

SITE_URL = environment.get_str("SITE_URL", required=True)

AUTHENTICATION_BACKENDS = ['hypatio.auth0authenticate.Auth0Authentication', 'django.contrib.auth.backends.ModelBackend']

SSL_SETTING = "https"
VERIFY_REQUESTS = True

CONTACT_FORM_RECIPIENTS="dbmi_tech_core@hms.harvard.edu"
DEFAULT_FROM_EMAIL="dbmi_tech_core@hms.harvard.edu"

RECAPTCHA_KEY = environment.get_str('RECAPTCHA_KEY', required=True)
RECAPTCHA_CLIENT_ID = environment.get_str('RECAPTCHA_CLIENT_ID', required=True)

##########
# S3 Configurations
S3_BUCKET = environment.get_str('S3_BUCKET', required=True)

DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
AWS_STORAGE_BUCKET_NAME = environment.get_str('S3_BUCKET', required=True)
AWS_LOCATION = 'upload'

##########

# Internationalization
# https://docs.djangoproject.com/en/1.10/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Absolute filesystem path to the Django project directory:
DJANGO_ROOT = dirname(dirname(abspath(__file__)))

# Absolute filesystem path to the top-level project folder:
SITE_ROOT = dirname(DJANGO_ROOT)

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.10/howto/static-files/

##########
# STATIC FILE CONFIGURATION
DJANGO_ROOT = dirname(dirname(abspath(__file__)))
# THIS IS WHERE FILES ARE COLLECTED INTO.
STATIC_ROOT = normpath(join(DJANGO_ROOT, 'assets'))
STATIC_URL = '/static/'

# THIS IS WHERE FILES ARE COLLECTED FROM
STATICFILES_DIRS = (
    normpath(join(DJANGO_ROOT, 'static')),
)

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

##########
# DJANGO-COUNTRIES CONFIGURATION
COUNTRIES_FLAG_URL = STATIC_URL + 'flags/{code}.gif'
COUNTRIES_OVERRIDE = {'':''}
COUNTRIES_FIRST = ['']

##########
# MEDIA FILE CONFIGURATION
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

##########

#####################################################################################
# DBMI Client Configurations
#####################################################################################

DBMI_CLIENT_CONFIG = {
    'CLIENT': 'hypatio',
    'ENVIRONMENT': environment.get_str('DBMI_ENV', required=True),
    'ENABLE_LOGGING': True,
    'LOG_LEVEL': environment.get_int('DBMI_LOG_LEVEL', default=logging.WARNING),

    # AuthZ
    'AUTHZ_ADMIN_GROUP': 'hypatio-admins',
    'AUTHZ_ADMIN_PERMISSION': 'ADMIN',
    'JWT_COOKIE_DOMAIN': environment.get_str('COOKIE_DOMAIN', required=True),
    'AUTHN_TITLE': 'DBMI Portal',

    # Set auth configurations
    'AUTH_CLIENTS': environment.get_dict('AUTH_CLIENTS', required=True),

    # Fileservice
    'FILESERVICE_URL': environment.get_str('FILESERVICE_API_URL', required=True),
    'FILESERVICE_GROUP': environment.get_str('FILESERVICE_GROUP', required=True),
    'FILESERVICE_BUCKETS': [environment.get_str('FILESERVICE_AWS_BUCKET', required=True)],
    'FILESERVICE_TOKEN': environment.get_str('FILESERVICE_SERVICE_TOKEN', required=True),

    # Misc
    'DRF_OBJECT_OWNER_KEY': 'email',
}

#####################################################################################

#####################################################################################
# Email Configurations
#####################################################################################

EMAIL_BACKEND = environment.get_str("EMAIL_BACKEND", "django_smtp_ssl.SSLEmailBackend")
EMAIL_USE_SSL = EMAIL_BACKEND == 'django_smtp_ssl.SSLEmailBackend'
EMAIL_HOST = environment.get_str("EMAIL_HOST", required=True)
EMAIL_HOST_USER = environment.get_str("EMAIL_HOST_USER", required=not DEBUG)
EMAIL_HOST_PASSWORD = environment.get_str("EMAIL_HOST_PASSWORD", required=EMAIL_HOST_USER is not None)
EMAIL_PORT = environment.get_str("EMAIL_PORT", required=True)

#####################################################################################

#####################################################################################
# FileService Configurations
#####################################################################################

FILESERVICE_API_URL = environment.get_str('FILESERVICE_API_URL', required=True)
FILESERVICE_GROUP = environment.get_str('FILESERVICE_GROUP', required=True)
FILESERVICE_AWS_BUCKET = environment.get_str('FILESERVICE_AWS_BUCKET', required=True)
FILESERVICE_SERVICE_ACCOUNT = 'hypatio'
FILESERVICE_SERVICE_TOKEN = environment.get_str('FILESERVICE_SERVICE_TOKEN', required=True)
FILESERVICE_AUTH_HEADER_PREFIX = 'Token'

#####################################################################################

#####################################################################################
# Django-Q settings
#####################################################################################

Q_CLUSTER = {
    'name': 'hypatio',
    'workers': 8,
    'recycle': 500,
    'timeout': 18000,
    'compress': True,
    'save_limit': 250,
    'queue_limit': 500,
    'cpu_affinity': 1,
    'retry': 20000,
    'label': 'Hypatio Tasks',
    'orm': 'default',
    'guard_cycle': 60,
}

#####################################################################################

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'console': {
            'format': '[HYPATIO] - [%(asctime)s][%(levelname)s][%(name)s.%(funcName)s:%(lineno)d] - %(message)s',
        },
    },
    'handlers': {
        'sentry': {
            'level': 'ERROR',
            'class': 'raven.contrib.django.raven_compat.handlers.SentryHandler',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'console',
            'stream': sys.stdout,
        },
    },
    'root': {
        'handlers': ['console', ],
        'level': 'DEBUG'
    },
    'loggers': {
        'django': {
            'handlers': ['console', ],
            'level': 'INFO',
            'propagate': True,
        },
        'raven': {
            'level': 'WARNING',
            'handlers': ['console'],
            'propagate': False,
        },
        'sentry.errors': {
            'level': 'WARNING',
            'handlers': ['console'],
            'propagate': False,
        },
        'botocore': {
            'level': 'WARNING',
            'handlers': ['console'],
            'propagate': True,
        },
        'boto3': {
            'level': 'WARNING',
            'handlers': ['console'],
            'propagate': True,
        },
        's3transfer': {
            'level': 'WARNING',
            'handlers': ['console'],
            'propagate': True,
        },
    },
}

RAVEN_CONFIG = {
    'dsn': environment.get_str("RAVEN_URL", required=True),
    # If you are using git, you can also automatically configure the
    # release based on the git info.
    'release': '1',
    'site': 'HYPATIO'
}
