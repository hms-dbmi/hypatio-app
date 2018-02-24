import requests
import json
from django.conf import settings
from furl import furl
from json import JSONDecodeError
import logging
logger = logging.getLogger(__name__)

VERIFY_SSL = True


def build_headers_with_jwt(user_jwt):
    return {"Authorization": "JWT " + user_jwt, 'Content-Type': 'application/json'}


def send_confirmation_email(user_jwt, current_uri):
    send_confirm_email_url = settings.SCIREG_REGISTRATION_URL + 'send_confirmation_email/'

    logger.debug("[HYPATIO][DEBUG][send_confirmation_email] - Sending user confirmation e-mail to " + send_confirm_email_url)

    email_confirm_data = {
        'success_url': current_uri,
        'project': 'hypatio',
    }

    requests.post(send_confirm_email_url, headers=build_headers_with_jwt(user_jwt), data=json.dumps(email_confirm_data))


def check_email_confirmation(user_jwt):

    response = requests.get(settings.SCIREG_REGISTRATION_URL, headers=build_headers_with_jwt(user_jwt))

    try:
        email_status = response.json()['results'][0]['email_confirmed']
    except KeyError:
        email_status = None
    except IndexError:
        email_status = None

    return email_status


def get_user_profile(user_jwt, email_of_profile, project):

    f = furl(settings.SCIREG_REGISTRATION_URL)

    f.args["email"] = email_of_profile
    f.args["project"] = project

    try:
        profile = requests.get(f.url, headers=build_headers_with_jwt(user_jwt)).json()
    except JSONDecodeError:
        profile = {"count": 0}

    return profile
