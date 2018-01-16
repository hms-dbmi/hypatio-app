import json
import logging
import sys
import requests
from datetime import datetime

from django.conf import settings
from django.contrib.auth import logout
from django.shortcuts import render, redirect
from pyauth0jwt.auth0authenticate import user_auth_and_jwt, public_user_auth_and_jwt, validate_jwt, logout_redirect

from .models import DataChallenge

from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.contrib import messages

from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from socket import gaierror

# Get an instance of a logger
logger = logging.getLogger(__name__)

@user_auth_and_jwt
def signout(request):
    logout(request)
    response = redirect(settings.AUTH0_LOGOUT_URL)
    response.delete_cookie('DBMI_JWT', domain=settings.COOKIE_DOMAIN)
    return response

@public_user_auth_and_jwt
def list_data_challenges(request, template_name='datachallenges/list.html'):

    all_data_challenges = DataChallenge.objects.all()
    data_challenges = []

    if not request.user.is_authenticated():
        user = None
        user_logged_in = False
    else:
        user = request.user
        user_logged_in = True
        user_jwt = request.COOKIES.get("DBMI_JWT", None)

        # If the JWT has expired or the user doesn't have one, force the user to login again
        if user_jwt is None or validate_jwt(request) is None:
            logout_redirect(request)

        # The JWT token that will get passed in API calls
        jwt_headers = {"Authorization": "JWT " + user_jwt, 'Content-Type': 'application/json'}

        # Build the dictionary with all project and permission information needed
        for data_challenge in all_data_challenges:
            
            # Package all the necessary information into one dictionary
            challenge = {"name": data_challenge.name,
                    "short_description": data_challenge.short_description,
                    "description": data_challenge.description,
                    "challenge_key": data_challenge.challenge_key,
                    "permission_scheme": data_challenge.permission_scheme}

            data_challenges.append(challenge)
        
        # TODO 
        is_manager = True

    return render(request, template_name, {"data_challenges": data_challenges,
                                           "user_logged_in": user_logged_in,
                                           "user": user,
                                           "ssl_setting": settings.SSL_SETTING,
                                           "is_manager": is_manager,
                                           "account_server_url": settings.ACCOUNT_SERVER_URL,
                                           "profile_server_url": settings.SCIREG_SERVER_URL})
