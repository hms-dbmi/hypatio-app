import requests
import json

from furl import furl
from json import JSONDecodeError

from django.conf import settings


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


def get_user_email_confirmation_status(user_jwt):
    """
    Makes a request to SciReg to see if this user has verified their email address.
    Returns True or False.
    """

    response = requests.get(settings.SCIREG_REGISTRATION_URL, headers=build_headers_with_jwt(user_jwt))

    try:
        email_status = response.json()['results'][0]['email_confirmed']
    except KeyError:
        email_status = False
    except IndexError:
        email_status = False

    return email_status


def get_current_user_profile(user_jwt):

    f = furl(settings.SCIREG_REGISTRATION_URL)

    try:
        profile = requests.get(f.url, headers=build_headers_with_jwt(user_jwt)).json()

    except JSONDecodeError:
        profile = {"count": 0}

    return profile


def get_user_profile(user_jwt, email_of_profile, project):

    f = furl(settings.SCIREG_REGISTRATION_URL)

    f.args["email"] = email_of_profile
    f.args["project"] = 'Hypatio.' + project

    try:
        profile = requests.get(f.url, headers=build_headers_with_jwt(user_jwt)).json()
    except JSONDecodeError:
        profile = {"count": 0}

    return profile


def get_distinct_countries_participating(user_jwt, participants, project):
    """
    Takes a QuerySet of participants' emails and returns a dictionary
    containing the unique countries of these participants and a count for each.
    """

    url = settings.SCIREG_REGISTRATION_URL + 'get_countries/'

    # From a QuerySet of participants, get a list of their emails
    emails = list(participants.values_list('user__email', flat=True))
    emails_list_string = ",".join(emails)

    data = {
        'emails': emails_list_string,
        'project': 'Hypatio.' + project,
    }

    try:
        countries = requests.post(url, headers=build_headers_with_jwt(user_jwt), data=json.dumps(data)).json()
    except Exception:
        logger.error('Failed to get country list from SciReg.')
        return None

    return countries
