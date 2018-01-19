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

from profile.views import user_has_manage_permission

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

    is_manager = False

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

        # TODO Does this user have MANAGE permissions on any item?
        is_manager = user_has_manage_permission(request, 'N2C2')

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

    return render(request, template_name, {"data_challenges": data_challenges,
                                           "user_logged_in": user_logged_in,
                                           "user": user,
                                           "ssl_setting": settings.SSL_SETTING,
                                           "is_manager": is_manager,
                                           "account_server_url": settings.ACCOUNT_SERVER_URL,
                                           "profile_server_url": settings.SCIREG_SERVER_URL})

@user_auth_and_jwt
def manage_contests(request, template_name='datachallenges/managecontests.html'):

    all_data_challenges = DataChallenge.objects.all()
    data_challenges = []

    # TODO eventually this shouldn't be hard coded for n2c2
    data_challenge = "N2C2"

    # This dictionary will hold all user requests and permissions
    user_details = {}

    user = request.user
    user_logged_in = True
    user_jwt = request.COOKIES.get("DBMI_JWT", None)

    # If the JWT has expired or the user doesn't have one, force the user to login again
    if user_jwt is None or validate_jwt(request) is None:
        logout_redirect(request)

    # Confirm that the user has MANAGE permissions for this item
    is_manager = user_has_manage_permission(request, data_challenge)

    if not is_manager:
        logger.debug('[HYPATIO][DEBUG] User ' + user.email + ' does not have MANAGE permissions for item ' + data_challenge + '.')
        return HttpResponse(403)
    
    # The JWT token that will get passed in API calls
    jwt_headers = {"Authorization": "JWT " + user_jwt, 'Content-Type': 'application/json'}

    authorization_request_url = settings.AUTHORIZATION_REQUEST_URL + "?item=" + data_challenge
    logger.debug('[HYPATIO][DEBUG] authorization_request_url: ' + authorization_request_url)

    # Query SciAuthZ for all access requests to this contest
    authorization_requests = requests.get(authorization_request_url, headers=jwt_headers, verify=False).json()
    logger.debug('[HYPATIO][DEBUG] Item Permission Requests: ' + json.dumps(authorization_requests))

    if authorization_requests is not None and 'results' in authorization_requests:
        authorization_requests_json = authorization_requests['results']

        for authorization_request in authorization_requests_json:

            date_requested = ""
            date_request_granted = ""

            if authorization_request['date_requested'] is not None:
                date_requested = datetime.strftime(datetime.strptime(authorization_request['date_requested'], "%Y-%m-%dT%H:%M:%S"), "%b %d %Y, %H:%M:%S")

            if authorization_request['date_request_granted'] is not None:
                date_request_granted = datetime.strftime(datetime.strptime(authorization_request['date_request_granted'], "%Y-%m-%dT%H:%M:%S"), "%b %d %Y, %H:%M:%S")

            # Store the permission request in a dictionary and include a blank permissions key to be added later
            user_detail = {'personal_information': {'first_name': '',
                                                    'last_name': ''},
                           'authorization_request': {'date_requested': date_requested,
                                                     'request_granted': authorization_request['request_granted'],
                                                     'date_request_granted': date_request_granted,
                                                     'request_id': authorization_request['id']},
                           'permissions': []}

            # Add a key to the user details dictionary with the user email as the key and permis
            user_details[authorization_request['user']] = user_detail

    # Query SciAuthZ for all permissions to this contest
    permissions_url = settings.USER_PERMISSIONS_URL + "?item=" + data_challenge
    user_permissions = requests.get(permissions_url, headers=jwt_headers, verify=False).json()
    logger.debug('[HYPATIO][DEBUG] User Permissions: ' + json.dumps(user_permissions))

    if user_permissions is not None and 'results' in user_permissions:
        user_permissions = user_permissions["results"]

        for permission in user_permissions:

            # If this user is not already in the user detail dictionary, add them (user does not have a permission request apparently)
            if permission['user'] not in user_details:
                user_details[permission['user']] = {'personal_information': {'first_name': '',
                                                                             'last_name': ''},
                                                    'authorization_request': '',
                                                    'permissions': ''}

            # Add this permission to the user details dictionary
            user_details[permission['user']]['permissions'].append(permission['permission'])

    logger.debug('[HYPATIO][DEBUG] user_details: ' + json.dumps(user_details))

    return render(request, template_name, {"user_logged_in": user_logged_in,
                                           "user": user,
                                           "ssl_setting": settings.SSL_SETTING,
                                           "is_manager": is_manager,
                                           "user_details": user_details,
                                           "project": data_challenge})

@user_auth_and_jwt
def grant_access_with_view_permissions(request):

    user = request.user
    user_jwt = request.COOKIES.get("DBMI_JWT", None)
    jwt_headers = {"Authorization": "JWT " + user_jwt, 'Content-Type': 'application/json'}

    project = request.POST['project']
    person_email = request.POST['user_email']
    authorization_request_id = request.POST['authorization_request_id']

    current_time = datetime.strftime(datetime.now(), "%Y-%m-%dT%H:%M:%S")

    logger.debug('[HYPATIO][DEBUG] Granting authorization request ' + authorization_request_id + ' and view permissions to ' + person_email + ' for project ' + project + '.')

    is_manager = user_has_manage_permission(request, project)

    if not is_manager:
        logger.debug('[HYPATIO][DEBUG] User ' + user.email + ' does not have MANAGE permissions for item ' + project + '.')
        return HttpResponse(403)

    # Grab the full authorization request object from SciAuthZ to have all fields necessary for serialization
    authorization_request_url = settings.AUTHORIZATION_REQUEST_URL + "?id=" + authorization_request_id
    authorization_request = requests.get(authorization_request_url, headers=jwt_headers, verify=False).json()

    if authorization_request is not None and 'results' in authorization_request:
        authorization_request_data = authorization_request['results'][0]
        logger.debug('[HYPATIO][DEBUG] authorization_request_data ' + json.dumps(authorization_request_data))
    else:
        # This authorization request should have been found
        return HttpResponse(404)

    # Update the granted flag in the authorization request
    authorization_request_data['request_granted'] = True
    authorization_request_data['date_request_granted'] = current_time

    authorization_request_url = settings.AUTHORIZATION_REQUEST_GRANT_URL + authorization_request_id + '/'
    requests.put(authorization_request_url, headers=jwt_headers, data=json.dumps(authorization_request_data), verify=False)

    user_permission = {"user": person_email,
                       "item": project,
                       "permission": "VIEW",
                       "date_updated": current_time}

    # Add a VIEW permission to the user
    permissions_url = settings.USER_PERMISSIONS_URL
    user_permissions = requests.post(permissions_url, headers=jwt_headers, data=json.dumps(user_permission), verify=False)

    return HttpResponse(200)
