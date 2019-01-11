from json import JSONDecodeError

import requests
import json
import furl
import logging

from django.conf import settings

from projects.models import DataProject

logger = logging.getLogger(__name__)

class SciAuthZ:
    USER_PERMISSIONS_URL = None
    JWT_HEADERS = None
    CURRENT_USER_EMAIL = None

    def __init__(self, authz_base, jwt, user_email):

        user_permissions_url = authz_base + "/user_permission/"
        create_profile_permission = authz_base + "/user_permission/create_registration_permission_record/"
        create_view_permission = authz_base + "/user_permission/create_item_view_permission_record/"
        remove_view_permission = authz_base + "/user_permission/remove_item_view_permission_record/"

        self.USER_PERMISSIONS_URL = user_permissions_url
        self.CREATE_PROFILE_PERMISSION = create_profile_permission
        self.CREATE_ITEM_PERMISSION = create_view_permission
        self.REMOVE_ITEM_PERMISSION = remove_view_permission

        jwt_headers = {"Authorization": "JWT " + jwt, 'Content-Type': 'application/json'}

        self.JWT_HEADERS = jwt_headers
        self.CURRENT_USER_EMAIL = user_email

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
        """
        Make a request to DBMI-AuthZ to pull down all the user permissions that
        the user has attached to their email. AuthZ paginates their results, so
        keep looping requests until there are no pages left.
        """

        next_page = True
        authz_url = self.USER_PERMISSIONS_URL + "?email=" + self.CURRENT_USER_EMAIL
        user_permissions = []

        try:
            while next_page:
                user_permissions_request = requests.get(
                    authz_url,
                    headers=self.JWT_HEADERS,
                    verify=settings.VERIFY_REQUESTS
                ).json()

                # If there are any permissions returned, add them to the list.
                if 'results' in user_permissions_request:
                    user_permissions = user_permissions + user_permissions_request['results']

                # If there are more permissions to pull, update the URL to hit. Otherwise, exit the loop.
                if 'next' in user_permissions_request and user_permissions_request['next'] is not None:
                    authz_url = user_permissions_request['next']
                else:
                    next_page = False

        except JSONDecodeError:
            user_permissions = None

        return user_permissions

    # TODO is this creating 3 times over??
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
            return False

        if user_permissions is not None and 'results' in user_permissions:
            # A user may have multiple permissions, check if one of them is the one we're looking for
            for permission in user_permissions["results"]:
                if permission["permission"] == value:
                    return True

        return False

    def user_has_any_manage_permissions(self):
        """
        A method used to see if this user has MANAGE permissions for any project within this application.
        """

        user_permissions = self.current_user_permissions()

        for permission in user_permissions:
            if 'Hypatio' in permission['item'] and permission['permission'] == "MANAGE":
                return True

        return False

    def get_projects_managed_by_user(self):
        """
        Returns a list of DataProject objects managed by the user.
        """

        user_permissions = self.current_user_permissions()
        managing_items = []

        for permission in user_permissions:

            # Go through the list of Hypatio related items that the user managers
            if 'Hypatio' in permission['item'] and permission['permission'] == "MANAGE":

                # Pull out the name of the item, which comes between the first and (optional) second period in the permission string
                item_list = permission['item'].split('.')
                managing_items.append(item_list[1])

        projects_managed = DataProject.objects.filter(project_key__in=managing_items)
        return projects_managed

    def get_all_view_permissions_for_project(self, project):
        """
        Returns a list of emails for users who have VIEW permissions for a project.
        """

        authz_url = self.USER_PERMISSIONS_URL + "?item=Hypatio." + project
        next_page = True
        users = []

        try:
            while next_page:
                user_permissions_request = requests.get(
                    authz_url,
                    headers=self.JWT_HEADERS,
                    verify=settings.VERIFY_REQUESTS
                ).json()

                # If there are any permissions returned, add them to the list.
                if 'results' in user_permissions_request:
                    for result in user_permissions_request['results']:
                        if 'user_email' in result:
                            users.append(result['user_email'])

                # If there are more permissions to pull, update the URL to hit. Otherwise, exit the loop.
                if 'next' in user_permissions_request and user_permissions_request['next'] is not None:
                    authz_url = user_permissions_request['next']
                else:
                    next_page = False

        except JSONDecodeError:
            user_permissions = None

        return users
