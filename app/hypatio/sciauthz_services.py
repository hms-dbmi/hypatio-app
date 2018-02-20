from json import JSONDecodeError

import requests
import json
import logging

logger = logging.getLogger(__name__)

class SciAuthZ:
    USER_PERMISSIONS_URL = None
    JWT_HEADERS = None
    CURRENT_USER_EMAIL = None
    AUTHORIZATION_REQUEST_URL = None

    VERIFY_REQUEST = False

    def __init__(self, authz_base, jwt, user_email):

        user_permissions_url = authz_base + "/user_permission/"
        authorization_request_url = authz_base + "/authorization_requests/"
        authorization_request_grant_url = authz_base + "/authorization_request_change/"
        create_profile_permission = authz_base + "/user_permission/create_registration_permission_record/"

        self.USER_PERMISSIONS_URL = user_permissions_url
        self.AUTHORIZATION_REQUEST_URL = authorization_request_url
        self.CREATE_PROFILE_PERMISSION = create_profile_permission

        jwt_headers = {"Authorization": "JWT " + jwt, 'Content-Type': 'application/json'}

        self.JWT_HEADERS = jwt_headers
        self.CURRENT_USER_EMAIL = user_email
        self.AUTHORIZATION_REQUEST_GRANT_URL = authorization_request_grant_url

    # Check if this user has SciAuthZ manage permissions on the given item
    def user_has_manage_permission(self, request, item):

        is_manager = False

        # Confirm user is a manager of the given project
        permissions_url = self.USER_PERMISSIONS_URL + "?item=" + item + "&email=" + self.CURRENT_USER_EMAIL

        try:
            user_permissions = requests.get(permissions_url, headers=self.JWT_HEADERS, verify=self.VERIFY_REQUEST).json()
        except JSONDecodeError:
            user_permissions = None

        if user_permissions is not None and 'results' in user_permissions:
            for perm in user_permissions['results']:
                if perm['permission'] == "MANAGE":
                    is_manager = True

        return is_manager

    def current_user_permissions(self):

        try:
            user_permissions = requests.get(self.USER_PERMISSIONS_URL + "?email=" + self.CURRENT_USER_EMAIL, headers=self.JWT_HEADERS, verify=self.VERIFY_REQUEST).json()
        except JSONDecodeError:
            user_permissions = None

        return user_permissions

    def current_user_access_requests(self):

        try:
            user_access_requests = requests.get(self.AUTHORIZATION_REQUEST_URL, headers=self.JWT_HEADERS, verify=self.VERIFY_REQUEST).json()
        except JSONDecodeError:
            user_access_requests = None

        return user_access_requests

    def current_user_request_access(self, access_request):
        try:
            user_access_request = requests.post(self.AUTHORIZATION_REQUEST_URL, headers=self.JWT_HEADERS, data=json.dumps(access_request), verify=self.VERIFY_REQUEST)
        except JSONDecodeError:
            user_access_request = None

        return user_access_request

    def create_profile_permission(self, grantee_email):
        logger.debug('[HYPATIO][create_profile_permission] - Creating Profile Permissions')

        modified_headers = self.JWT_HEADERS

        modified_headers['Content-Type'] = 'application/x-www-form-urlencoded'

        profile_permission = requests.post(self.CREATE_PROFILE_PERMISSION, headers=modified_headers, data={"grantee_email": grantee_email}, verify=self.VERIFY_REQUEST)

        return profile_permission