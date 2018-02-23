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

from os.path import normpath, join, dirname, abspath
from django.utils.crypto import get_random_string

chars = 'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)'

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.10/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get("SECRET_KEY", get_random_string(50, chars))

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

PROJECT = 'hypatio'

ALLOWED_HOSTS = [os.environ.get("ALLOWED_HOSTS")]

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'jquery',
    'bootstrap3',
    'contact',
    'django_countries',
    'profile',
    'projects',
    'pyauth0jwt',
    'raven.contrib.django.raven_compat',
]

MIDDLEWARE_CLASSES = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'hypatio.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [normpath(join(BASE_DIR, 'templates'))],
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
        'USER': os.environ.get("MYSQL_USERNAME"),
        'PASSWORD': os.environ.get("MYSQL_PASSWORD"),
        'HOST': os.environ.get("MYSQL_HOST"),
        'PORT': os.environ.get("MYSQL_PORT"),
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

SITE_URL = os.environ.get("SITE_URL")

AUTH0_DOMAIN = os.environ.get("AUTH0_DOMAIN")
AUTH0_CLIENT_ID = os.environ.get("AUTH0_CLIENT_ID")
AUTH0_SECRET = os.environ.get("AUTH0_SECRET")
AUTH0_SUCCESS_URL = os.environ.get("AUTH0_SUCCESS_URL")
AUTH0_LOGOUT_URL = os.environ.get("AUTH0_LOGOUT_URL","")

AUTHENTICATION_BACKENDS = ['pyauth0jwt.auth0authenticate.Auth0Authentication', 'django.contrib.auth.backends.ModelBackend']

AUTHENTICATION_LOGIN_URL = os.environ.get("ACCOUNT_SERVER_URL")
ACCOUNT_SERVER_URL = os.environ.get("ACCOUNT_SERVER_URL")
SCIREG_SERVER_URL = os.environ.get("SCIREG_SERVER_URL", "")
AUTHZ_BASE = os.environ.get("AUTHZ_BASE", "")

USER_PERMISSIONS_URL = AUTHZ_BASE + "/user_permission/"
AUTHORIZATION_REQUEST_URL = AUTHZ_BASE + "/authorization_requests/"
AUTHORIZATION_REQUEST_GRANT_URL = AUTHZ_BASE + "/authorization_request_change/"

SCIREG_REGISTRATION_URL = SCIREG_SERVER_URL + "/api/register/"

COOKIE_DOMAIN = os.environ.get("COOKIE_DOMAIN")

SSL_SETTING = "https"

CONTACT_FORM_RECIPIENTS="dbmi_tech_core@hms.harvard.edu"
DEFAULT_FROM_EMAIL="dbmi_tech_core@hms.harvard.edu"

RECAPTCHA_KEY = os.environ.get('RECAPTCHA_KEY')
RECAPTCHA_CLIENT_ID = os.environ.get('RECAPTCHA_CLIENT_ID')

EMAIL_CONFIRM_SUCCESS_URL = os.environ.get('EMAIL_CONFIRM_SUCCESS_URL')

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
    normpath(join(DJANGO_ROOT, 'media'))
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

EMAIL_BACKEND = 'django_smtp_ssl.SSLEmailBackend'
EMAIL_USE_SSL = True
EMAIL_HOST = os.environ.get("EMAIL_HOST")
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD")
EMAIL_PORT = os.environ.get("EMAIL_PORT")

LOGGING = {
    'version': 1,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'stream': sys.stdout,
        },
        'file_debug': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'debug.log',
        },
        'file_error': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': 'error.log',
        }
    },
    'root': {
        'handlers': ['console', 'file_debug'],
        'level': 'DEBUG'
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file_error'],
            'level': 'ERROR',
            'propagate': True,
        },
    },
}

RAVEN_CONFIG = {
    'dsn': os.environ.get("RAVEN_URL", ""),
    # If you are using git, you can also automatically configure the
    # release based on the git info.
    'release': '1',
}

try:
    from .local_settings import *
except ImportError:
    pass
