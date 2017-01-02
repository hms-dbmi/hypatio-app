from django.shortcuts import render
from stronghold.decorators import public
from dataprojects.models import DataProject
from django.conf import settings
import jwt
import base64
from django.contrib import auth as django_auth
from django.contrib.auth import login
import logging
import requests
import json

# Get an instance of a logger
logger = logging.getLogger(__name__)


def request_access(request, template_name='dataprojects/access_request.html'):

    user_jwt = request.COOKIES.get("DBMI_JWT", None)
    jwt_headers = {"Authorization": "JWT " + user_jwt, 'Content-Type': 'application/json'}

    project_permissions_setup = settings.PROJECT_SETUP_URL + request.POST['project_key']

    # ------------------
    # Get Project Permissions & Requirements
    r = requests.get(project_permissions_setup, headers=jwt_headers)

    try:
        dua_text = r.json()["results"][0]["dua"][0]["agreement_text"]
        dua_name = r.json()["results"][0]["dua"][0]["name"]
        dua = r.json()["results"][0]["dua_required"]
        grant_required = r.json()["results"][0]["permission_scheme"] == "PRIVATE"
    except:
        dua_text = ""
        dua = True
        grant_required = True
    # ------------------

    return render(request, template_name, {"dua": dua,
                                           "grant_required": grant_required,
                                           "dua_text": dua_text,
                                           "project_key": request.POST['project_key'],
                                           "data_use_agreement": dua_name})


def submit_request(request, template_name='dataprojects/submit_request.html'):

    user_jwt = request.COOKIES.get("DBMI_JWT", None)
    jwt_headers = {"Authorization": "JWT " + user_jwt, 'Content-Type': 'application/json'}

    data_request = {'project': request.POST['project_key'], 'user': request.user.email}
    data_dua_sign = {'data_use_agreement': request.POST['data_use_agreement'], 'user': request.user.email}

    create_auth_request_url = settings.CREATE_REQUEST_URL
    create_dua_sign_request_url = settings.CREATE_DUA_SIGN

    requests.post(create_auth_request_url, headers=jwt_headers, data=json.dumps(data_request))
    requests.post(create_dua_sign_request_url, headers=jwt_headers, data=json.dumps(data_dua_sign))

    return render(request, template_name)

@public
def listDataprojects(request, template_name='dataprojects/list.html'):
    user = None

    permission_dictionary = {}
    project_permission_setup = {}
    access_request_dictionary = {}

    # If not logged in, check for cookie with JWT.
    if not request.user.is_authenticated():
        try:
            jwt_string = request.COOKIES.get("DBMI_JWT", None)
            payload = jwt.decode(jwt_string, base64.b64decode(settings.AUTH0_SECRET, '-_'), algorithms=['HS256'],
                                 audience=settings.AUTH0_CLIENT_ID)
            request.session['profile'] = payload
            user = django_auth.authenticate(**payload)

            if user:
                login(request, user)
        except jwt.InvalidTokenError:
            logger.error("No/Bad JWT Token.")

    all_data_projects = DataProject.objects.all()

    # Okay, definitely not a real user.
    if not request.user.is_authenticated():
        user_logged_in = False
    else:
        user_logged_in = True
        user = request.user

        user_jwt = request.COOKIES.get("DBMI_JWT", None)

        if user_jwt:

            jwt_headers = {"Authorization": "JWT " + user_jwt, 'Content-Type': 'application/json'}

            permissions_url = settings.PERMISSION_SERVER
            project_permissions_setup = settings.PROJECT_PERMISSION_URL
            access_requests_url = settings.GET_ACCESS_REQUESTS

            # ------------------
            # Get Project Permissions & Requirements
            r = requests.get(project_permissions_setup, headers=jwt_headers)

            try:
                for project_setup in r.json()["results"]:
                    for project in all_data_projects:
                            if project.project_key == project_setup["project_key"]:
                                project_permission_setup[project.project_key] = project_setup
            except:
                project_permission_setup = {}
            # ------------------

            # ------------------
            # Get user permissions.
            r = requests.get(permissions_url, headers=jwt_headers)

            try:
                for project_permission in r.json()["results"]:
                    for project in all_data_projects:
                        if project.project_key == project_permission["project"]:
                            permission_dictionary[project.project_key] = project_permission["permission"]
            except:
                permission_dictionary = {}
            # ------------------


            # ------------------
            # Find what requests for access the user has already made.
            r = requests.get(access_requests_url, headers=jwt_headers)

            try:
                for access_request in r.json()["results"]:
                    for project in all_data_projects:
                        if project.project_key == access_request["project"]:
                            access_request_dictionary[project.project_key] = {
                                "date_requested": access_request["date_requested"],
                                "request_granted": access_request["request_granted"],
                                "date_request_granted": access_request["request_granted"],
                            }
            except:
                access_request_dictionary = {}
            # ------------------

    return render(request, template_name, {"dataprojects": all_data_projects,
                                           "user_logged_in": user_logged_in,
                                           "user": user,
                                           "account_server_url": settings.ACCOUNT_SERVER_URL,
                                           "permission_dictionary": permission_dictionary,
                                           "project_permission_setup": project_permission_setup,
                                           "access_request_dictionary": access_request_dictionary})
