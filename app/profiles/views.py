import json
import logging
import sys
import requests
from datetime import datetime

from django.conf import settings
from django.contrib.auth import logout
from django.shortcuts import render, redirect
from pyauth0jwt.auth0authenticate import public_user_auth_and_jwt

from .forms import UserProfileForm

from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.contrib import messages

from django.template.loader import render_to_string

# Get an instance of a logger
logger = logging.getLogger(__name__)

@public_user_auth_and_jwt
def profile(request, template_name='profiles/profile.html'):

    # Set initial values.
    initial = {
        'first_name': 'test',
        'last_name': 'test',
        'email': 'test',
        'street_address1': 'test',
        'street_address2': 'test',
        'city': 'test',
        'state': 'test',
        'zipcode': 'test',
        'phone_number': 'test'
    }

    # Generate and render the form.
    form = UserProfileForm(initial=initial)
    return render(request, template_name, {'user_profile_form': form})
