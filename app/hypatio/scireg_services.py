import requests
import json
from django.conf import settings

import logging
logger = logging.getLogger(__name__)


def build_headers_with_jwt(user_jwt):
    return {"Authorization": "JWT " + user_jwt, 'Content-Type': 'application/json'}


def send_confirmation_email(user_jwt, current_uri):
    send_confirm_email_url = settings.SCIREG_REGISTRATION_URL + 'send_confirmation_email/'

    logger.debug("[P2M2][DEBUG][send_confirmation_email] - Sending user confirmation e-mail to " + send_confirm_email_url)

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