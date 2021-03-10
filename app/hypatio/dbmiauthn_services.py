from functools import wraps
from pyauth0jwt.auth0authenticate import validate_request, jwt_login
from django.conf import settings
from django.contrib import auth
import logging
logger = logging.getLogger(__name__)


class DBMIAuthn:

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
                auth.logout(request)

            # User has a JWT session open but not a Django session. Try to start a Django session and continue the request.
            if not request.user.is_authenticated and jwt_payload is not None:
                jwt_login(request, jwt_payload)

            return function(request, *args, **kwargs)

        return wrap
