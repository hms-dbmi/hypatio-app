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

    # If there was a POST request, a form was submitted
    if request.method == 'POST':

        # Process the form
        form = UserProfileForm(request.POST)
        if form.is_valid():

            # The SciReg API endpoint
            registration_url = settings.SCIREG_SERVER_URL + '/api/register/' + form.cleaned_data['id'] + '/'

            logger.debug('[HYPATIO][DEBUG] Profile form fields submitted: ' + json.dumps(form.cleaned_data))            

            # Send the data to SciReg
            requests.put(registration_url, headers=jwt_headers, data=json.dumps(form.cleaned_data), verify=False)

            # Generate and render the form.
            return render(request, template_name, {'form': form,
                                                   'user': user,
                                                   'user_logged_in': user_logged_in})
        else:
            logger.debug('[HYPATIO][DEBUG] Profile form errors: ' + form.errors.as_json())

            # TODO send this back to profile to display errors
            return HttpResponse(status=500)

    else:

        # The SciReg API endpoint
        registration_url = settings.SCIREG_SERVER_URL + '/api/register/'

        # Query SciReg to get the user's information
        registration_info = requests.get(registration_url, headers=jwt_headers, verify=False).json()

        if registration_info is not None:
            registration_info = registration_info["results"]
        else:
            # TODO user does not have a registration in scireg, what should we do?
            pass

        logger.debug('[HYPATIO][DEBUG] Registration info ' + json.dumps(registration_info))

        # Generate and render the form.
        form = UserProfileForm(initial=registration_info[0])
        return render(request, template_name, {'form': form,
                                               'user': user,
                                               'user_logged_in': user_logged_in})

