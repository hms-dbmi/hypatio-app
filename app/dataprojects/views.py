import json
import logging
import sys
import requests
import furl
from datetime import datetime

from django.conf import settings
from django.contrib.auth import logout
from django.shortcuts import render, redirect
from pyauth0jwt.auth0authenticate import user_auth_and_jwt, public_user_auth_and_jwt, validate_jwt, logout_redirect

from .models import DataProject, DataUseAgreement, DataUseAgreementSign

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

@user_auth_and_jwt
def request_access(request, template_name='dataprojects/access_request.html'):

    project = DataProject.objects.get(project_key=request.POST['project_key'])

    # There may be multiple DUAs for a project for the user to choose from
    data_use_agreements = DataUseAgreement.objects.filter(project=project).values()

    return render(request, template_name, {"project_key": request.POST['project_key'],
                                           "data_use_agreements": data_use_agreements})

@user_auth_and_jwt
def submit_request(request):

    user_jwt = request.COOKIES.get("DBMI_JWT", None)
    jwt_headers = {"Authorization": "JWT " + user_jwt, 'Content-Type': 'application/json'}

    dua = DataUseAgreement.objects.get(id=request.POST['dua_id'])

    date_requested = datetime.now().isoformat()

    # Save the signed DUA
    dua_signed = DataUseAgreementSign(data_use_agreement=dua,
                                      user=request.user,
                                      date_signed=date_requested,
                                      agreement_text=request.POST['agreement_text'])
    dua_signed.save()

    data_request = {"user": request.user.email,
                    "item": request.POST['project_key']}

    # Send the authorization request to SciAuthZ
    create_auth_request_url = settings.AUTHORIZATION_REQUEST_URL
    requests.post(create_auth_request_url, headers=jwt_headers, data=json.dumps(data_request), verify=False)

    return HttpResponse(200)

@public_user_auth_and_jwt
def list_data_projects(request, template_name='dataprojects/list.html'):

    all_data_projects = DataProject.objects.all()

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
                   "project_url": project.project_url,
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
