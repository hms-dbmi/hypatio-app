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

# Get an instance of a logger
logger = logging.getLogger(__name__)

@public
def listDataprojects(request, template_name='dataprojects/list.html'):
    user = None

    permission_dictionary = {}

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

        # Get user permissions.
        permissions_url = settings.PERMISSION_SERVER
        user_jwt = request.COOKIES.get("DBMI_JWT", None)
        jwt_headers = {"Authorization": "JWT " + user_jwt, 'Content-Type': 'application/json'}
        r = requests.get(permissions_url, headers=jwt_headers)

        try:
            for project_permission in r.json()["results"]:
                for project in all_data_projects:
                    if project.project_key == project_permission["project"]:
                        permission_dictionary["BERSON"] = project_permission["permission"]
        except:
            permission_dictionary = {}

    return render(request, template_name, {"dataprojects": all_data_projects,
                                           "user_logged_in": user_logged_in,
                                           "user": user,
                                           "account_server_url": settings.ACCOUNT_SERVER_URL,
                                           "permission_dictionary": permission_dictionary})
