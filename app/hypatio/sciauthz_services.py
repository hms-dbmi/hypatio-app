from json import JSONDecodeError

import requests
import json
import furl
import logging

from django.conf import settings

logger = logging.getLogger(__name__)

class SciAuthZ:
    USER_PERMISSIONS_URL = None
    JWT_HEADERS = None
    CURRENT_USER_EMAIL = None
    AUTHORIZATION_REQUEST_URL = None

    def __init__(self, authz_base, jwt, user_email):

        user_permissions_url = authz_base + "/user_permission/"
        authorization_request_url = authz_base + "/authorization_requests/"
        authorization_request_grant_url = authz_base + "/authorization_request_change/"
        create_profile_permission = authz_base + "/user_permission/create_registration_permission_record/"
        create_view_permission = authz_base + "/user_permission/create_item_view_permission_record/"
        remove_view_permission = authz_base + "/user_permission/remove_item_view_permission_record/"

        self.USER_PERMISSIONS_URL = user_permissions_url
        self.AUTHORIZATION_REQUEST_URL = authorization_request_url
        self.CREATE_PROFILE_PERMISSION = create_profile_permission
        self.CREATE_ITEM_PERMISSION = create_view_permission
        self.REMOVE_ITEM_PERMISSION = remove_view_permission

        jwt_headers = {"Authorization": "JWT " + jwt, 'Content-Type': 'application/json'}

        self.JWT_HEADERS = jwt_headers
        self.CURRENT_USER_EMAIL = user_email
        self.AUTHORIZATION_REQUEST_GRANT_URL = authorization_request_grant_url

    # Check if this user has SciAuthZ manage permissions on the given item
    def user_has_manage_permission(self, item):

        is_manager = False
        sciauthz_item = 'Hypatio.' + item

        # Confirm user is a manager of the given project
        permissions_url = self.USER_PERMISSIONS_URL + "?item=" + sciauthz_item + "&email=" + self.CURRENT_USER_EMAIL

        try:
            user_permissions = requests.get(permissions_url, headers=self.JWT_HEADERS, verify=settings.VERIFY_REQUESTS).json()
        except JSONDecodeError:
            user_permissions = None

        if user_permissions is not None and 'results' in user_permissions:
            for perm in user_permissions['results']:
                if perm['permission'] == "MANAGE":
                    is_manager = True

        return is_manager

    def current_user_permissions(self):

        try:
            user_permissions = requests.get(self.USER_PERMISSIONS_URL + "?email=" + self.CURRENT_USER_EMAIL, headers=self.JWT_HEADERS, verify=settings.VERIFY_REQUESTS).json()
        except JSONDecodeError:
            user_permissions = None

        return user_permissions

    def current_user_access_requests(self):

        try:
            user_access_requests = requests.get(self.AUTHORIZATION_REQUEST_URL, headers=self.JWT_HEADERS, verify=settings.VERIFY_REQUESTS).json()
        except JSONDecodeError:
            user_access_requests = None

        return user_access_requests

    def current_user_request_access(self, access_request):
        try:
            user_access_request = requests.post(self.AUTHORIZATION_REQUEST_URL, headers=self.JWT_HEADERS, data=json.dumps(access_request), verify=settings.VERIFY_REQUESTS)
        except JSONDecodeError:
            user_access_request = None

        return user_access_request

    def create_profile_permission(self, grantee_email, project):
        logger.debug('[HYPATIO][create_profile_permission] - Creating Profile Permissions')

        modified_headers = self.JWT_HEADERS
        modified_headers['Content-Type'] = 'application/x-www-form-urlencoded'

        data = {
            "grantee_email": grantee_email,
            "item": 'Hypatio.' + project
        }

        profile_permission = requests.post(
            self.CREATE_PROFILE_PERMISSION,
            headers=modified_headers,
            data=data,
            verify=settings.VERIFY_REQUESTS
        )

        return profile_permission

    def create_view_permission(self, project, grantee_email):
        logger.debug('[HYPATIO][create_view_permission] - Creating VIEW permission for ' + grantee_email + ' on project ' + project + '.')

        modified_headers = self.JWT_HEADERS
        modified_headers['Content-Type'] = 'application/x-www-form-urlencoded'

        context = {
            "grantee_email": grantee_email,
            "item": 'Hypatio.' + project
        }

        view_permission = requests.post(self.CREATE_ITEM_PERMISSION, headers=modified_headers, data=context, verify=settings.VERIFY_REQUESTS)
        return view_permission

    def remove_view_permission(self, project, grantee_email):
        logger.debug('[HYPATIO][remove_view_permission] - Removing VIEW permission for ' + grantee_email + ' on project ' + project + '.')

        modified_headers = self.JWT_HEADERS
        modified_headers['Content-Type'] = 'application/x-www-form-urlencoded'

        context = {
            "grantee_email": grantee_email,
            "item": 'Hypatio.' + project
        }

        view_permission = requests.post(self.REMOVE_ITEM_PERMISSION, headers=modified_headers, data=context, verify=settings.VERIFY_REQUESTS)
        return view_permission

    def user_has_single_permission(self, permission, value):

        f = furl.furl(self.USER_PERMISSIONS_URL)
        f.args["item"] = 'Hypatio.' + permission

        try:
            user_permissions = requests.get(f.url, headers=self.JWT_HEADERS, verify=settings.VERIFY_REQUESTS).json()
        except JSONDecodeError:
            logger.debug("[SCIAUTHZ][user_has_single_permission] - No Valid permissions returned.")
            user_permissions = {"count": 0}

        if user_permissions["count"] > 0:

            # A user may have multiple permissions, check if one of them is the one we're looking for
            for permission in user_permissions["results"]:
                if permission["permission"] == value:
                    return True

            return False
        else:
            return False

    def user_has_any_manage_permissions(self):
        """
        A method used to see if this user has MANAGE permissions for any project within this application.
        """

        user_permissions = self.current_user_permissions()

        if user_permissions is not None and 'results' in user_permissions:
            for permission in user_permissions["results"]:
                if 'Hypatio' in permission['item'] and permission['permission'] == "MANAGE":
                    return True

        return False
