from furl import furl
import json
import base64
import logging
import requests
from functools import wraps

from django.contrib.auth.models import User
from django.contrib import auth as django_auth
from django.contrib.auth import login
from django.conf import settings
from django.shortcuts import redirect
from django.contrib.auth import logout
from django.core.exceptions import PermissionDenied
from dbmi_client.settings import dbmi_settings
from dbmi_client.settings import dbmi_settings
from dbmi_client.authn import validate_request, login_redirect_url, get_jwt_payload, get_jwt

logger = logging.getLogger(__name__)


def jwt_and_manage(item):
    '''
    Decorator that accepts an item string that is used to retrieve
    permissions from SciAuthZ. The current user must have a valid JWT
    and also have 'MANAGE' permissions for the passed item.
    :param item: The SciAuthZ item string
    :type item: str
    :return: function
    '''

    def real_decorator(function):

        @wraps(function)
        def wrap(request, *args, **kwargs):

            # Validates the JWT and returns its payload if valid.
            jwt_payload = validate_request(request)

            # User has a valid JWT from SciAuth
            if jwt_payload is not None:

                content = None
                try:
                    # Get the email
                    email = jwt_payload.get('email')

                    # Confirm user is a manager of the given project
                    permissions_url = sciauthz_permission_url(item, email)
                    response = requests.get(permissions_url, headers=sciauthz_headers(request))
                    content = response.content
                    response.raise_for_status()

                    # Parse permissions
                    user_permissions = response.json()

                    if user_permissions is not None and 'results' in user_permissions:
                        for perm in user_permissions['results']:
                            if perm['permission'] == "MANAGE":
                                return function(request, *args, **kwargs)

                    # Possibly store these elsewhere for records
                    logger.warning('{} Failed MANAGE permission on {}'.format(email, item),
                                   extra={'jwt': jwt_payload, 'authorizations': response.json()})

                except requests.HTTPError as e:
                    logger.exception('Checking permissions error: {}'.format(e), exc_info=True,
                                     extra={'jwt': jwt_payload, 'content': content})

                except Exception as e:
                    logger.exception('Checking permissions error: {}'.format(e), exc_info=True,
                                     extra={'jwt': jwt_payload})

                # Forbid access as a default measure
                raise PermissionDenied

            else:
                logger.debug('Missing/invalid JWT, sending to login')
                return logout_redirect(request)

        return wrap

    return real_decorator


def public_user_auth_and_jwt(function):

    @wraps(function)
    def wrap(request, *args, **kwargs):
        """
        Here we see if the user is logged in but let them stay on the page if they aren't.
        """

        # Validates the JWT and returns its payload if valid.
        jwt_payload = validate_request(request)

        # If user is logged in, make sure they have a valid JWT
        if request.user.is_authenticated and jwt_payload is None:
            logger.debug('User ' + request.user.email + ' is authenticated but does not have a valid JWT. Logging them out.')
            return logout_redirect(request)

        # User has a JWT session open but not a Django session. Try to start a Django session and continue the request.
        if not request.user.is_authenticated and jwt_payload is not None:
            jwt_login(request, jwt_payload)

        return function(request, *args, **kwargs)

    return wrap


def user_auth_and_jwt(function):
    '''
    Decorator to verify both the JWT as well as the session
    of the current user in order to control access to the
    given method or view. JWT email is also compared to the
    Django user's email and must match. Redirects back to
    authentication server if not all conditions are satisfied.
    :param function: The protected method
    :return: decorator
    '''
    @wraps(function)
    def wrap(request, *args, **kwargs):

        # Validates the JWT and returns its payload if valid.
        jwt_payload = validate_request(request)

        # User is both logged into this app and via JWT.
        if request.user.is_authenticated and jwt_payload is not None:

            # Ensure the email matches (without case sensitivity)
            if request.user.username.lower() != jwt_payload['email'].lower():
                logger.debug('Django and JWT email mismatch! Log them out and redirect to log back in')
                return logout_redirect(request)

            return function(request, *args, **kwargs)
        # User has a JWT session open but not a Django session. Start a Django session and continue the request.
        elif not request.user.is_authenticated and jwt_payload is not None:
            if jwt_login(request, jwt_payload):
                return function(request, *args, **kwargs)
            else:
                return logout_redirect(request)
        # User doesn't pass muster, throw them to the login app.
        else:
            return logout_redirect(request)

    return wrap


def dbmi_jwt(function):
    '''
    Decorator to only check if the current user's JWT is valid
    :param function:
    :type function:
    :return:
    :rtype:
    '''
    @wraps(function)
    def wrap(request, *args, **kwargs):

        # Validates the JWT and returns its payload if valid.
        jwt_payload = validate_request(request)

        # User has a valid JWT from SciAuth
        if jwt_payload is not None:
            return function(request, *args, **kwargs)

        else:
            logger.debug('Missing/invalid JWT, sending to login')
            return logout_redirect(request)

    return wrap


def sciauthz_permission_url(item, email):
    '''
    Build and return the SciAuthZ URL to GET against for a user's
    item permissions
    :param item: The SciAuthZ item to check permissions on
    :type item: str
    :param email: The email of the user in questions
    :type email: str
    :return: The URL
    :rtype: str
    '''
    # Build it
    url = furl(settings.PERMISSIONS_URL)

    # Add query
    url.query.params.add('item', item)
    url.query.params.add('email', email)

    return url.url


def sciauthz_headers(request):
    '''
    Returns the headers needed to authenticate requests against SciAuthZ
    :param request:
    :type request:
    :return:
    :rtype:
    '''

    # Extract JWT token into a string.
    jwt_string = request.COOKIES.get("DBMI_JWT", None)

    return {"Authorization": "JWT " + jwt_string, 'Content-Type': 'application/json'}


def jwt_login(request, jwt_payload):
    """
    The user has a valid JWT but needs to log into this app. Do so here and return the status.
    :param request:
    :param jwt_payload: String form of the JWT.
    :return:
    """

    logger.debug("Logging user in via JWT. Is Authenticated? " + str(request.user.is_authenticated))

    request.session['profile'] = jwt_payload

    user = django_auth.authenticate(request, **jwt_payload)

    if user:
        login(request, user)
    else:
        logger.debug("Could not log user in.")

    return request.user.is_authenticated


def logout_redirect(request):
    """
    This will log a user out and redirect them to log in again via the AuthN server.
    :param request:
    :return: The response object that takes the user to the login page. 'next' parameter set to bring them back to their intended page.
    """
    logout(request)

    # Build the URL
    login_url = furl(login_redirect_url(request, next_url=request.build_absolute_uri()))

    # Check for branding
    if hasattr(settings, 'SCIAUTH_BRANDING'):
        logger.debug('SciAuth branding passed')

        # Encode it and pass it
        branding = base64.urlsafe_b64encode(json.dumps(settings.SCIAUTH_BRANDING).encode('utf-8')).decode('utf-8')
        login_url.query.params.add('branding', branding)

    # Set the URL and purge cookies
    response = redirect(login_url.url)
    response.delete_cookie('DBMI_JWT', domain=dbmi_settings.JWT_COOKIE_DOMAIN)
    logger.debug('Redirecting to: {}'.format(login_url.url))

    return response


class Auth0Authentication(object):

    def authenticate(self, request, **token_dictionary):

        # Get the JWT payload
        payload = get_jwt_payload(request, verify=True)
        if not payload:
            return None

        logger.debug("Authenticate User: {}/{}".format(payload.get('sub'), payload.get('email')))

        try:
            user = User.objects.get(username=payload["email"])
        except User.DoesNotExist:
            logger.debug("User not found, creating: {}".format(payload.get('email')))

            user = User(username=payload["email"], email=payload["email"])
            user.save()
        return user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
