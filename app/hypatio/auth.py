from functools import wraps

import requests
from django.core.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission
from django.contrib import auth as django_auth
from django.core.exceptions import PermissionDenied
from rest_framework.authentication import BaseAuthentication
from rest_framework import exceptions
from django.contrib import auth as django_auth
from django.core.exceptions import PermissionDenied
from django.http import QueryDict
from rest_framework.request import Request
from dbmi_client.authn import validate_request
from dbmi_client.settings import dbmi_settings

from hypatio.auth0authenticate import validate_request
from hypatio.sciauthz_services import SciAuthZ
from hypatio.dbmiauthz_services import DBMIAuthz
from hypatio.auth0authenticate import logout_redirect

import logging
logger = logging.getLogger(__name__)


class DBMIAPIUser(BaseAuthentication):
    """
    Authentication method for DBMI API methods
    """
    def authenticate(self, request):

        # Get the JWT
        token = validate_request(request)
        if not token:
            raise exceptions.NotAuthenticated

        # Call the standard Django authenticate method, that will in
        # turn call Hypatio.Auth0Authentication.authenticate
        user = django_auth.authenticate(request, **token)
        if not user:
            raise exceptions.AuthenticationFailed

        # Return the user's email to attach to the request object (request.user)
        # Also, return the authz dictionary contained in the JWT claims, if present (request.auth)
        return user, None


class DataProjectManagerPermission(BasePermission):
    """
    Permission check for owner or manage/admin permissions on PPM
    'obj' in this context is the FHIR ID of the Patient to performs ops for
    """
    permission_item = 'Project'
    message = 'User does not have proper permission on project'

    def has_object_permission(self, request, view, obj):
        """
        Ensures the requesting user has MANAGE permissions on the passed project

        :param request: The current request
        :type request: HttpRequest
        :param view: The view the request is being made to
        :type view: View
        :param obj: The project key for which the request is being made
        :type obj: str
        """
        # Get the JWT
        user_jwt = request.COOKIES.get("DBMI_JWT", None)

        # Check permissions in DBMI AuthZ
        sciauthz = SciAuthZ(user_jwt, request.user.email)
        is_manager = sciauthz.user_has_manage_permission(obj)

        # Log it if check has failed and raise exception
        if not is_manager:
            logger.debug(
                f'User {request.user.email} does not have MANAGE permissions for "{obj}".'
            )
            raise PermissionDenied

        logger.debug(
            f'User {request.user.email} does have MANAGE permissions for "{obj}".'
        )
        return True


def data_project_manager(project_key_arg: str = 'project_key'):
    '''
    Decorator that ensures the calling user has MANAGE permissions on the
    DataProject identified by the project_key_arg parameter.

    :param project_key_arg: The key of the argument that specifies the project
    :type project_key_arg: str
    '''

    def real_decorator(function):

        @wraps(function)
        def wrap(request, *args, **kwargs):

            # Attempt to get project key
            project_key = kwargs.get(project_key_arg, None)

            # Check if this is a DRF request
            if not project_key and isinstance(request, Request):

                # Check data and query params
                project_key = request.data.get(project_key_arg, request.query_params.get(project_key_arg, None))

            if not project_key and request.body:

                # Check the request body
                body = QueryDict(request.body)
                project_key = body.get(project_key_arg, None)

            # If not passed in URL, check request type and inspect respective data
            if not project_key and request.method == 'GET':

                # Check GET
                project_key = request.GET.get(project_key_arg, None)

            if not project_key and request.method == 'POST':

                # Check POST
                project_key = request.POST.get(project_key_arg, None)

            if not project_key:
                logger.error(f"Missing project key argument: {project_key_arg}")
                raise PermissionDenied(f"Missing project key argument: {project_key_arg}")

            # Validates the JWT and returns its payload if valid.
            jwt_payload = validate_request(request)

            # User has a valid JWT from SciAuth
            if jwt_payload is not None:
                email = jwt_payload.get('email')

                # Check permissions
                if DBMIAuthz.user_has_manage_permission(project_key, email):
                    return function(request, *args, **kwargs)

                # Possibly store these elsewhere for records
                logger.warning(f'{email} Failed MANAGE permission on {project_key}', extra={'jwt': jwt_payload})

                raise PermissionDenied

            else:
                logger.debug('Missing/invalid JWT, sending to login')
                return logout_redirect(request)

        return wrap

    return real_decorator
