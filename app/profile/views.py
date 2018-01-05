import json
import logging
import sys
import requests
from datetime import datetime

from django.conf import settings
from django.contrib.auth import logout
from django.shortcuts import render, redirect
from pyauth0jwt.auth0authenticate import user_auth_and_jwt, validate_jwt, logout_redirect

from .forms import UserProfileForm

from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.contrib import messages

from django.template.loader import render_to_string

# Get an instance of a logger
logger = logging.getLogger(__name__)

@user_auth_and_jwt
def profile(request, template_name='profile/profile.html'):

    user = request.user
    user_logged_in = True
    user_jwt = request.COOKIES.get("DBMI_JWT", None)

    # If the JWT has expired or the user doesn't have one, force the user to login again
    if user_jwt is None or validate_jwt(request) is None:
        logout_redirect(request)

    # The JWT token that will get passed in API calls
    jwt_headers = {"Authorization": "JWT " + user_jwt, 'Content-Type': 'application/json'}

    # Query SciReg to get the user's information
    registration_url = settings.SCIREG_SERVER_URL + '/api/register'
    registration_info = requests.get(registration_url, headers=jwt_headers, verify=False).json()["results"]

    # Populate the form with the returned registration info
    form_values = {
        'first_name': registration_info[0]['first_name'],
        'last_name': registration_info[0]['last_name'],
        'email': registration_info[0]['email'],
        'street_address1': registration_info[0]['street_address1'],
        'street_address2': registration_info[0]['street_address2'],
        'city': registration_info[0]['city'],
        'state': registration_info[0]['state'],
        'zipcode': registration_info[0]['zipcode'],
        'phone_number': registration_info[0]['phone_number']
    }

    # Generate and render the form.
    form = UserProfileForm(initial=form_values)
    return render(request, template_name, {'user_profile_form': form,
                                           'user': user,
                                           'user_logged_in': user_logged_in})
