import requests
from furl import furl
import logging

from django.core.exceptions import ObjectDoesNotExist
from dbmi_client.settings import dbmi_settings

from projects.models import DataProject
from projects.models import Participant

logger = logging.getLogger(__name__)


class DBMIAuthz:

    user_permissions_url = dbmi_settings.AUTHZ_URL + "/user_permission/"
    create_profile_permission_url = dbmi_settings.AUTHZ_URL + "/user_permission/create_registration_permission_record/"
    create_view_permission_url = dbmi_settings.AUTHZ_URL + "/user_permission/create_item_view_permission_record/"
    remove_view_permission_url = dbmi_settings.AUTHZ_URL + "/user_permission/remove_item_view_permission_record/"

    @classmethod
    def _permissions_query(cls, request, email=None, item=None, search=None):
        """
        This is a utility method for any AuthZ query. It ensures results are properly paged.
        :param request: The current user request context
        :param email: The email of the person for whom permissions apply (if None, calling user must have permissions
                      to lookup permissions of other users)
        :param item: The item to check permissions on (e.g. 'Hypatio', 'Hypatio.n2c2-t2')
        :param search: Any search parameters, comma separated (email and permission is 'iexact', item is 'contains'
                       Searching can include any number of parameters but will only be compared to `item`, `permission`
                       and `email`
        :return:
        """
        # Get request objects
        jwt = request.COOKIES.get("DBMI_JWT")
        if not jwt:
            raise ValueError('Cannot request permissions without valid JWT')

        # Set url
        url = furl(DBMIAuthz.user_permissions_url)

        # Build parameters
        params = {}
        if email:
            params['email'] = email
        else:
            params['email'] = request.user.email
        if item:
            params['item'] = item
        if search:
            params['search'] = search

        # Set headers
        headers = {"Authorization": "JWT " + jwt, 'Content-Type': 'application/json'}

        # Page until we have no more URLs returned
        permissions = []
        content = None
        while url is not None:
            try:
                # Make the request
                response = requests.get(url=url.url, headers=headers, params=params)
                content = response.content
                response.raise_for_status()

                # Parse result
                results = response.json()

                # If there are any permissions returned, add them to the list.
                if 'results' in results:
                    permissions.extend(results['results'])

                # If there are more permissions to pull, update the URL to hit. Otherwise, exit the loop.
                url = furl.furl(results['next']) if results.get('next') else None

            except Exception as e:
                logger.exception(f'AuthZ Error: {e}', exc_info=True, extra={
                    'url': url, 'params': params, 'content': content,
                })

        return permissions

    @classmethod
    def _permissions_post(cls, request, url, data):
        """
        This is a utility method for modifying an AuthZ permission via POST.
        :param request: The current user request context
        :param url: Where to POST
        :param data: The dictionary of data to send in the body of the request
        :return:
        """
        # Get request objects
        jwt = request.COOKIES.get("DBMI_JWT")
        if not jwt:
            raise ValueError('Cannot modify permissions without valid JWT')

        # Set headers
        headers = {"Authorization": "JWT " + jwt, 'Content-Type': 'application/x-www-form-urlencoded'}

        content = None
        try:
            # Make the request
            response = requests.post(url=url.url, headers=headers, data=data)
            content = response.content
            response.raise_for_status()

            # Return response
            return response

        except Exception as e:
            logger.exception(f'AuthZ Error: {e}', exc_info=True, extra={
                'url': url, 'data': data, 'content': content,
            })

    ###################################################################################################################
    # CREATE
    ###################################################################################################################

    @classmethod
    def create_profile_permission(cls, request, project_key, grantee_email):
        """
        Creates a permission that allows once user to lookup another user's profile on DBMI-Reg
        :param request: The current request context
        :param project_key: The project to limit lookups to
        :param grantee_email: The email of the person to apply the permission
        :return: Response
        """
        logger.debug(f'[HYPATIO][create_profile_permission] - Creating profile permission for {grantee_email} '
                     f'on project Hypatio.{project_key}.')

        data = {
            "grantee_email": grantee_email,
            "item": 'Hypatio.' + project_key
        }

        return cls._permissions_post(request=request, url=cls.create_profile_permission_url, data=data)

    @classmethod
    def create_view_permission(cls, request, project_key, grantee_email):
        """
        Creates a permission that allows once user to view a project in Hypatio
        :param request: The current request context
        :param project_key: The project to limit lookups to
        :param grantee_email: The email of the person to apply the permission
        :return: Response
        """
        logger.debug(f'[HYPATIO][create_view_permission] - Creating VIEW permission for {grantee_email} '
                     f'on project Hypatio.{project_key}.')

        data = {
            "grantee_email": grantee_email,
            "item": 'Hypatio.' + project_key
        }

        return cls._permissions_post(request=request, url=cls.create_view_permission_url, data=data)

    ###################################################################################################################
    # READ
    ###################################################################################################################

    @classmethod
    def user_has_manage_permission(cls, request, project_key):
        """
        Checks permissions in AuthZ server and returns whether the calling user has MANAGE on the passed
        project or MANAGE on Hypatio globally.
        :param request: The current request context
        :param project_key: The project to limit lookups to
        :return: bool
        """
        logger.debug(f'[HYPATIO][user_has_manage_permission] - Checking MANAGE permission for {request.user.email}'
                     f' on project Hypatio.{project_key}')

        # Query current users' MANAGE permissions
        permissions = cls._permissions_query(request=request,  search='Hypatio,MANAGE')
        for perm in permissions:

            # Check for the specific permission
            if perm['item'] == f'Hypatio.{project_key}' and perm['permission'] == "MANAGE":
                return True

            # Check for a global MANAGE permission on all of Hypatio
            elif perm['item'] == 'Hypatio' and perm['permission'] == 'MANAGE':
                logger.debug(f'[HYPATIO][user_has_manage_permission] - {request.user.email} has global MANAGE '
                             f'permission for Hypatio -> MANAGE on Hypatio.{project_key}')
                return True

        return False

    @classmethod
    def user_has_view_permission(cls, request, project_key, email=None):
        """
        Checks permissions in AuthZ server and returns whether the calling user has VIEW or MANAGE on the passed
        project or MANAGE on Hypatio globally.
        :param request: The current request context
        :param project_key: The project to limit lookups to
        :param email: The email of the user to check permissions of, if not calling user
        :return: bool
        """
        logger.debug(f'[HYPATIO][user_has_view_permission] - Checking VIEW permission for {request.user.email}'
                     f' on project Hypatio.{project_key}')

        if not email:
            email = request.user.email

        # Check model first
        try:
            # Find the participant object
            participant = Participant.objects.get(project__project_key=project_key, user__email=email)

            # Check permission
            if participant.permission and participant.permission == 'VIEW' or participant.permission == 'MANAGE':
                logger.debug(f'[HYPATIO][user_has_view_permission] - {email} has local {participant.permission} '
                             f'permission for on project Hypatio.{project_key}')
                return True

        except ObjectDoesNotExist:
            pass

        # Query current users' permissions
        permissions = cls._permissions_query(request=request, email=email, search='Hypatio')
        for perm in permissions:

            # Check for specific permission
            if perm['item'] == f'Hypatio.{project_key}' and perm['permission'] == "VIEW" or perm['permission'] == "MANAGE":
                return True

            # Check for a global MANAGE permission on all of Hypatio
            elif perm['item'] == 'Hypatio' and perm['permission'] == 'MANAGE':
                logger.debug(f'[HYPATIO][user_has_view_permission] - {request.user.email} has global MANAGE '
                             f'permission for Hypatio -> VIEW on Hypatio.{project_key}')
                return True

        return False

    @classmethod
    def current_user_permissions(cls, request):
        """
        Checks permissions in AuthZ server and returns a list of each permission.
        :param request: The current request context
        :return: list
        """
        logger.debug(f'[HYPATIO][current_user_permissions] - Getting all permissions for {request.user.email}')

        return cls._permissions_query(request=request, search='Hypatio')

    @classmethod
    def user_has_single_permission(cls, request, project_key, permission, email=None):
        """
        Checks permissions in AuthZ server and returns whether the calling user has specific permission on the passed
        project or MANAGE on Hypatio globally.
        :param request: The current request context
        :param project_key: The project to limit lookups to
        :param permission: The permission to check
        :param email: The email of the user to check permissions of, if not calling user
        :return: bool
        """
        logger.debug(f'[HYPATIO][user_has_single_permission] - Checking {permission} permission for {request.user.email}'
                     f' on project Hypatio.{project_key}')

        # Set email
        if not email:
            email = request.user.email

        # A user may have multiple permissions, check if one of them is the one we're looking for
        for perm in cls._permissions_query(request=request, email=email, search='Hypatio'):

            # Check for specific permission
            if perm['item'] == f'Hypatio.{project_key}' and perm["permission"] == permission:
                return True

            # Check for a global MANAGE permission on all of Hypatio
            elif perm['item'] == 'Hypatio' and perm['permission'] == 'MANAGE':
                logger.debug(f'[HYPATIO][user_has_single_permission] - {request.user.email} has global MANAGE '
                             f'permission for Hypatio -> {permission} on Hypatio.{project_key}')
                return True

        return False

    @classmethod
    def user_has_any_manage_permissions(cls, request):
        """
        Checks permissions in AuthZ server and returns whether the calling user has MANAGE permission on any
        project or MANAGE on Hypatio globally.
        :param request: The current request context
        :return: bool
        """
        logger.debug(f'[HYPATIO][user_has_any_manage_permissions] - Checking any MANAGE permission for '
                     f'{request.user.email}')

        # A user may have multiple permissions, check if one of them is the one we're looking for
        if cls._permissions_query(request=request, search='Hypatio,MANAGE'):
            return True

        return False

    @classmethod
    def get_projects_managed_by_user(cls, request):
        """
        Checks permissions in AuthZ server and returns all permissions on Hypatio projects that are MANAGE
        :param request: The current request context
        :return: list
        """
        logger.debug(f'[HYPATIO][get_projects_managed_by_user] - Getting projects managed by {request.user.email}')

        # Collect managed projects
        managing_project_keys = []

        # A user may have multiple permissions, check if one of them is the one we're looking for
        for perm in cls._permissions_query(request=request, search='Hypatio,MANAGE'):
            # Check for absolute permission
            if perm['item'] == 'Hypatio' and perm['permission'] == "MANAGE":

                # This use has global MANAGE permissions, return everything
                logger.debug(f'[HYPATIO][get_projects_managed_by_user] - {request.user.email} has global MANAGE '
                             f'permission for Hypatio -> MANAGE on all projects')
                return DataProject.objects.all()

            # Go through the list of Hypatio related projects that the user managers
            elif 'Hypatio.' in perm['item'] and perm['permission'] == "MANAGE":

                # Determine project key from permission item
                item_list = perm['item'].split('.')
                managing_project_keys.append(item_list[1])

        # Return a queryset containing DataProject objects
        return DataProject.objects.filter(project_key__in=managing_project_keys)

    @classmethod
    def get_all_view_permissions_for_project(cls, request, project_key):
        """
        Checks permissions in AuthZ server and returns a list of all user emails that have VIEW permission on project.
        :param request: The current request context
        :param project_key: The project to limit lookups to
        :return: list
        """
        logger.debug(f'[HYPATIO][get_all_view_permissions_for_project] - Getting all users with permission VIEW'
                     f'on Hypatio.{project_key}')

        # Collect user emails
        users = []

        # Walk through permissions returned
        for perm in cls._permissions_query(request=request, item=f'Hypatio.{project_key}'):
            # Save string in lowercase.
            users.append(perm['user_email'].lower())

        return users

    ###################################################################################################################
    # UPDATE
    ###################################################################################################################

    # Nothing here yet...

    ###################################################################################################################
    # DELETE
    ###################################################################################################################

    @classmethod
    def remove_view_permission(cls, request, project_key, grantee_email):
        """
        This is a utility method for deleting an AuthZ permission
        :param request: The current request context
        :param project_key: The project permission to remove
        :param grantee_email: The email of the person in the permission to remove
        :return: Response
        """
        logger.debug(f'[HYPATIO][remove_view_permission] - Removing permission VIEW for {grantee_email}'
                     f'on Hypatio.{project_key}')
        data = {
            "grantee_email": grantee_email,
            "item": 'Hypatio.' + project_key
        }

        return cls._permissions_post(request=request, url=cls.remove_view_permission_url, data=data)
