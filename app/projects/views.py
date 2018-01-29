import json
import logging
import sys
import requests
import furl
from datetime import datetime

from django.conf import settings
from django.contrib.auth import logout
from django.shortcuts import render
from django.shortcuts import redirect
from pyauth0jwt.auth0authenticate import user_auth_and_jwt
from pyauth0jwt.auth0authenticate import public_user_auth_and_jwt
from pyauth0jwt.auth0authenticate import validate_jwt
from pyauth0jwt.auth0authenticate import logout_redirect

from .models import DataProject, Participant, Team

from profile.views import user_has_manage_permission

from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib import messages

from django.core.exceptions import ObjectDoesNotExist

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

@user_auth_and_jwt
def request_access(request, template_name='dataprojects/access_request.html'):

    project = DataProject.objects.get(project_key=request.POST['project_key'])
    agreement_forms = project.agreement_forms.all()

    return render(request, template_name, {"project_key": request.POST['project_key'],
                                           "agreement_forms": agreement_forms})

@user_auth_and_jwt
def submit_request(request):

    user_jwt = request.COOKIES.get("DBMI_JWT", None)
    jwt_headers = {"Authorization": "JWT " + user_jwt, 'Content-Type': 'application/json'}

    # TODO replace with newer models.
    
    # dua = DataUseAgreement.objects.get(id=request.POST['dua_id'])

    # date_requested = datetime.now().isoformat()

    # # Save the signed DUA
    # dua_signed = DataUseAgreementSign(data_use_agreement=dua,
    #                                   user=request.user,
    #                                   date_signed=date_requested,
    #                                   agreement_text=request.POST['agreement_text'])
    # dua_signed.save()

    # data_request = {"user": request.user.email,
    #                 "item": request.POST['project_key']}

    # # Send the authorization request to SciAuthZ
    # create_auth_request_url = settings.AUTHORIZATION_REQUEST_URL
    # requests.post(create_auth_request_url, headers=jwt_headers, data=json.dumps(data_request), verify=False)

    return HttpResponse(200)

@public_user_auth_and_jwt
def list_data_projects(request, template_name='dataprojects/list.html'):

    all_data_projects = DataProject.objects.filter(is_contest=False)

    data_projects = []
    projects_with_view_permissions = []
    projects_with_access_requests = {}

    is_manager = False

    # Build the login URL
    login_url = furl.furl(settings.ACCOUNT_SERVER_URL)

    # Add the next URL
    login_url.args.add('next', request.build_absolute_uri())

    # Add project, if any
    project = getattr(settings, 'PROJECT', None)
    if project is not None:
        login_url.args.add('project', project)

    # We want email verification by default so pass that success url too
    login_url.args.add('email_confirm_success_url', settings.EMAIL_CONFIRM_SUCCESS_URL)

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

        # Get all of the user's VIEW permissions
        permissions_url = settings.USER_PERMISSIONS_URL + "?email=" + user.email
        user_permissions = requests.get(permissions_url, headers=jwt_headers, verify=False).json()
        logger.debug('[HYPATIO][DEBUG] User Permissions: ' + json.dumps(user_permissions))

        if user_permissions is not None and 'results' in user_permissions:
            user_permissions = user_permissions["results"]

            for user_permission in user_permissions:
                if user_permission['permission'] == 'VIEW':
                    projects_with_view_permissions.append(user_permission['item'])

        # Get all of the user's permission requests
        access_requests_url = settings.AUTHORIZATION_REQUEST_URL + "?email=" + user.email
        logger.debug('[HYPATIO][DEBUG] access_requests_url: ' + access_requests_url)

        user_access_requests = requests.get(access_requests_url, headers=jwt_headers, verify=False).json()
        logger.debug('[HYPATIO][DEBUG] User Permission Requests: ' + json.dumps(user_access_requests))

        if user_access_requests is not None and 'results' in user_access_requests:
            user_access_requests = user_access_requests["results"]

            for access_request in user_access_requests:
                projects_with_access_requests[access_request['item']] = {
                    'date_requested': access_request['date_requested'],
                    'request_granted': access_request['request_granted'],
                    'date_request_granted': access_request['date_request_granted']}

    # Build the dictionary with all project and permission information needed
    for project in all_data_projects:

        user_has_view_permissions = project.project_key in projects_with_view_permissions

        if project.project_key in projects_with_access_requests:
            user_requested_access_on = projects_with_access_requests[project.project_key]['date_requested']
            user_requested_access = True
        else:
            user_requested_access_on = None
            user_requested_access = False

        # Package all the necessary information into one dictionary
        project = {"name": project.name,
                   "short_description": project.short_description,
                   "description": project.description,
                   "project_key": project.project_key,
                   # "project_url": project.project_url,
                   "permission_scheme": project.permission_scheme,
                   "user_has_view_permissions": user_has_view_permissions,
                   "user_requested_access": user_requested_access,
                   "user_requested_access_on": user_requested_access_on}

        data_projects.append(project)

    return render(request, template_name, {"data_projects": data_projects,
                                           "user_logged_in": user_logged_in,
                                           "user": user,
                                           "ssl_setting": settings.SSL_SETTING,
                                           "is_manager": is_manager,
                                           "login_url": login_url.url,
                                           "account_server_url": settings.ACCOUNT_SERVER_URL,
                                           "profile_server_url": settings.SCIREG_SERVER_URL})

@public_user_auth_and_jwt
def list_data_contests(request, template_name='datacontests/list.html'):

    all_data_contests = DataProject.objects.filter(is_contest=True)
    data_contests = []

    is_manager = False

    # Build the login URL
    login_url = furl.furl(settings.ACCOUNT_SERVER_URL)

    # Add the next URL
    login_url.args.add('next', request.build_absolute_uri())

    # Add project, if any
    project = getattr(settings, 'PROJECT', None)
    if project is not None:
        login_url.args.add('project', project)

    # We want email verification by default so pass that success url too
    login_url.args.add('email_confirm_success_url', settings.EMAIL_CONFIRM_SUCCESS_URL)

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

    logger.debug('HERE')
    # Build the dictionary with all project and permission information needed
    for data_contest in all_data_contests:
        logger.debug(data_contest.name)
        
        # Package all the necessary information into one dictionary
        contest = {"name": data_contest.name,
                        "short_description": data_contest.short_description,
                        "description": data_contest.description,
                        "project_key": data_contest.project_key,
                        "permission_scheme": data_contest.permission_scheme}

        data_contests.append(contest)

    return render(request, template_name, {"data_contests": data_contests,
                                           "user_logged_in": user_logged_in,
                                           "user": user,
                                           "ssl_setting": settings.SSL_SETTING,
                                           "is_manager": is_manager,
                                           "login_url": login_url.url,
                                           "account_server_url": settings.ACCOUNT_SERVER_URL,
                                           "profile_server_url": settings.SCIREG_SERVER_URL})

@user_auth_and_jwt
def manage_contests(request, template_name='datacontests/managecontests.html'):

    all_data_contests = DataProject.objects.filter(is_contest=True)
    data_contests = []

    # TODO eventually this shouldn't be hard coded for n2c2
    data_contest = "N2C2"

    # This dictionary will hold all user requests and permissions
    user_details = {}

    user = request.user
    user_logged_in = True
    user_jwt = request.COOKIES.get("DBMI_JWT", None)

    # If the JWT has expired or the user doesn't have one, force the user to login again
    if user_jwt is None or validate_jwt(request) is None:
        logout_redirect(request)

    # Confirm that the user has MANAGE permissions for this item
    is_manager = user_has_manage_permission(request, data_contest)

    if not is_manager:
        logger.debug('[HYPATIO][DEBUG] User ' + user.email + ' does not have MANAGE permissions for item ' + data_contest + '.')
        return HttpResponse(403)

    # The JWT token that will get passed in API calls
    jwt_headers = {"Authorization": "JWT " + user_jwt, 'Content-Type': 'application/json'}

    authorization_request_url = settings.AUTHORIZATION_REQUEST_URL + "?item=" + data_contest
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
    permissions_url = settings.USER_PERMISSIONS_URL + "?item=" + data_contest
    user_permissions = requests.get(permissions_url, headers=jwt_headers, verify=False).json()
    logger.debug('[HYPATIO][DEBUG] User Permissions: ' + json.dumps(user_permissions))

    if user_permissions is not None and 'results' in user_permissions:
        user_permissions = user_permissions["results"]

        for permission in user_permissions:

            # If this user is not already in the user detail dictionary, add them (user does not have a permission request apparently)
            if permission['user'] not in user_details:
                user_details[permission['user']] = {'personal_information': {'first_name': '',
                                                                             'last_name': ''},
                                                    'authorization_request': {},
                                                    'permissions': []}

            # Add this permission to the user details dictionary
            user_details[permission['user']]['permissions'].append(permission['permission'])

    logger.debug('[HYPATIO][DEBUG] user_details: ' + json.dumps(user_details))

    return render(request, template_name, {"user_logged_in": user_logged_in,
                                           "user": user,
                                           "ssl_setting": settings.SSL_SETTING,
                                           "is_manager": is_manager,
                                           "user_details": user_details,
                                           "project": data_contest})

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

@user_auth_and_jwt
def project_details(request, project_key, template_name='project_details.html'):

    project = DataProject.objects.get(project_key=project_key)
    agreement_forms = project.agreement_forms.all()

    access_granted = False

    if project is None:
        # TODO Hypatio needs a 404
        return HttpResponse(404)

    try:
        participant = Participant.objects.get(user=request.user)
    except ObjectDoesNotExist:
        participant = None

    try:
        teams = Team.objects.get(data_project__project_key=project_key)
    except ObjectDoesNotExist:
        teams = None

    return render(request, template_name, {"project": project,
                                           "agreement_forms": agreement_forms,
                                           "participant": participant,
                                           "teams": teams,
                                           "access_granted": access_granted})
