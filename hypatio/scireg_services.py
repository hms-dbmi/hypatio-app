import requests
from django.conf import settings


def build_headers_with_jwt(user_jwt):
    return {"Authorization": "JWT " + user_jwt, 'Content-Type': 'application/json'}


def request_project_access(user_jwt, project_key):

    jwt_headers = build_headers_with_jwt(user_jwt)

    project_permissions_setup = settings.PROJECT_SETUP_URL + project_key

    r = requests.get(project_permissions_setup, headers=jwt_headers)

    return r
