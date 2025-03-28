import os

from django.core.management.utils import get_random_secret_key

from dbmisvc_test.authentication import TestAuthentication

# Instantiate a test authentication system
TEST_AUTH = TestAuthentication()

os.environ["SECRET_KEY"] = get_random_secret_key()
os.environ["ALLOWED_HOSTS"] = "*"
os.environ["MYSQL_PASSWORD"] = ""
os.environ["MYSQL_HOST"] = ""
os.environ["SITE_URL"] = "https://portal.dbmi.hms.harvard.edu"
os.environ["CONTACT_FORM_RECIPIENTS"] = "support@dbmi.hms.harvard.edu"
os.environ["RECAPTCHA_KEY"] = ""
os.environ["RECAPTCHA_CLIENT_ID"] = ""
os.environ["S3_BUCKET"] = "portal-test-bucket"
os.environ["DBMI_ENV"] = "prod"
os.environ["COOKIE_DOMAIN"] = ".dbmi.hms.harvard.edu"
os.environ["AUTH_CLIENTS"] = TEST_AUTH.dbmisvc_client_auth_clients()
os.environ["FILESERVICE_URL"] = "https://fileservice.dbmi.hms.harvard.edu"
os.environ["FILESERVICE_API_URL"] = "https://fileservice.dbmi.hms.harvard.edu/filemaster"
os.environ["FILESERVICE_GROUP"] = "dbmi"
os.environ["FILESERVICE_AWS_BUCKET"] = "portal-test-bucket"
os.environ["FILESERVICE_SERVICE_ACCOUNT"] = "dbmi"
os.environ["FILESERVICE_SERVICE_TOKEN"] = get_random_secret_key()
os.environ["EMAIL_BACKEND"] = "django.core.mail.backends.locmem.EmailBackend"
os.environ["EMAIL_FROM_ADDRESS"] = "data-portal@dbmi.hms.harvard.edu"
os.environ["SENTRY_DSN"] = ""

from hypatio.settings import *

TEST_RUNNER = 'test.runners.HypatioTestRunner'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Make the 'static' folder available for loading templates
TEMPLATES[0]['DIRS'] += [os.path.join(BASE_DIR, 'static')]

# Force all asynchronous tasks to run synchronously
Q_CLUSTER["sync"] = True
