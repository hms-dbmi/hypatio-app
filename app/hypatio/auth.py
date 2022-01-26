import jwt
from furl import furl
import json
import base64
import logging
import requests
import jwcrypto.jwk as jwk
from functools import wraps

from django.contrib.auth.models import User
from django.contrib import auth as django_auth
from django.contrib.auth import login
from django.conf import settings
from django.shortcuts import redirect
from django.contrib.auth import logout
from django.core.exceptions import PermissionDenied

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

    def real_decorator(view):
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
                    response = requests.get(permissions_url, headers=sciauthz_headers(request), verify=verify_requests())
                    content = response.content
                    response.raise_for_status()

                    # Parse permissions
                    user_permissions = response.json()

                    if user_permissions is not None and 'results' in user_permissions:
                        for perm in user_permissions['results']:
                            if perm['permission'] == "MANAGE":
                                return view(request, *args, **kwargs)

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

        wrap.__doc__ = view.__doc__
        wrap.__name__ = view.__name__
        return wrap

    return real_decorator


def public_user_auth_and_jwt(view):
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

        return view(request, *args, **kwargs)

    return wrap


def user_auth_and_jwt(view):
    '''
    Decorator to verify both the JWT as well as the session
    of the current user in order to control access to the
    given method or view. JWT email is also compared to the
    Django user's email and must match. Redirects back to
    authentication server if not all conditions are satisfied.
    :param function: The protected method
    :return: decorator
    '''
    def wrap(request, *args, **kwargs):

        # Validates the JWT and returns its payload if valid.
        jwt_payload = validate_request(request)

        # User is both logged into this app and via JWT.
        if request.user.is_authenticated and jwt_payload is not None:

            # Ensure the email matches (without case sensitivity)
            if request.user.username.lower() != jwt_payload['email'].lower():
                logger.debug('Django and JWT email mismatch! Log them out and redirect to log back in')
                return logout_redirect(request)

            return view(request, *args, **kwargs)
        # User has a JWT session open but not a Django session. Start a Django session and continue the request.
        elif not request.user.is_authenticated and jwt_payload is not None:
            if jwt_login(request, jwt_payload):
                return view(request, *args, **kwargs)
            else:
                return logout_redirect(request)
        # User doesn't pass muster, throw them to the login app.
        else:
            return logout_redirect(request)

    return wrap


def dbmi_jwt(view):
    '''
    Decorator to only check if the current user's JWT is valid
    :param function:
    :type function:
    :return:
    :rtype:
    '''
    def wrap(request, *args, **kwargs):

        # Validates the JWT and returns its payload if valid.
        jwt_payload = validate_request(request)

        # User has a valid JWT from SciAuth
        if jwt_payload is not None:
            return view(request, *args, **kwargs)

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


def verify_requests():
    '''
    Checks settings to see if requests should be verified, defaults to True
    :return: Whether to verify requests or not
    :rtype: bool
    '''
    # Check for setting on verifying requests
    if hasattr(settings, 'VERIFY_REQUESTS'):
        return settings.VERIFY_REQUESTS

    # Log it
    logger.debug('VERIFY_REQUESTS setting is missing, defaulting to "True"')

    return True


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


def validate_jwt(request):
    """
    Determines if the JWT is valid based on expiration and signature evaluation.
    :param request:
    :return: None if JWT is invalid or missing.
    """
    # Extract JWT token into a string.
    jwt_string = request.COOKIES.get("DBMI_JWT", None)

    # Check that we actually have a token.
    if jwt_string is not None:

        # Attempt to validate the JWT (Checks both expiry and signature)
        try:
            payload = jwt.decode(jwt_string,
                                 base64.b64decode(settings.AUTH0_SECRET, '-_'),
                                 algorithms=['HS256'],
                                 leeway=120,
                                 audience=settings.AUTH0_CLIENT_ID)

            return payload

        except jwt.ExpiredSignatureError:
            logger.debug("JWT Expired.")

        except jwt.InvalidTokenError:
            logger.debug("Invalid JWT Token.")

        except Exception as e:
            logger.exception('Unexpected validation error: {}'.format(e), exc_info=True,
                             extra={'jwt': jwt_string})

    return None


def validate_request(request):
    '''
    Pulls the current cookie and verifies the JWT and
    then returns the JWT payload. Returns None
    if the JWT is invalid or missing.
    :param request: The Django request object
    :return: dict
    '''
    # Extract JWT token into a string.
    jwt_string = request.COOKIES.get("DBMI_JWT", None)

    # Check that we actually have a token.
    if jwt_string is not None:
        return validate_rs256_jwt(jwt_string)
    else:
        return None


def get_public_keys_from_auth0(refresh=False):
    '''
    Retrieves the public key from Auth0 to verify JWTs. Will
    cache the JSON response from Auth0 in Django settings
    until instructed to refresh the JWKS.
    :param refresh: Purges cached JWK and fetches from remote
    :return: dict
    '''

    # If refresh, delete cached key
    if refresh:
        delattr(settings, 'AUTH0_JWKS')

    jwks = None
    content = None
    try:
        # Look in settings
        if hasattr(settings, 'AUTH0_JWKS'):
            logger.debug('Using cached JWKS')

            # Parse the cached dict and return it
            return json.loads(settings.AUTH0_JWKS)

        else:

            logger.debug('Fetching remote JWKS')

            # Make the request
            response = requests.get("https://" + settings.AUTH0_DOMAIN + "/.well-known/jwks.json")
            content = response.content
            response.raise_for_status()

            # Parse it
            jwks = response.json()

            # Cache it
            setattr(settings, 'AUTH0_JWKS', json.dumps(jwks))

            return jwks

    except KeyError as e:
        logging.exception('Parsing public keys failed: {}'.format(e), exc_info=True,
                          extra={'domain': settings.AUTH0_DOMAIN, 'jwks': jwks})

    except json.JSONDecodeError as e:
        logging.exception('Parsing public keys failed: {}'.format(e), exc_info=True,
                          extra={'domain': settings.AUTH0_DOMAIN, 'jwks': jwks})

    except requests.HTTPError as e:
        logging.exception('Gettting public keys failed: {}'.format(e), exc_info=True,
                          extra={'domain': settings.AUTH0_DOMAIN, 'content': content})

    except Exception as e:
        logging.exception('Unexpected public key error: {}'.format(e), exc_info=True,
                          extra={'domain': settings.AUTH0_DOMAIN, 'content': content})

    return None


def retrieve_public_key(jwt_string):
    '''
    Gets the public key used to sign the JWT from the public JWK
    hosted on Auth0. Auth0 typically only returns one public key
    in the JWK set but to handle situations in which signing keys
    are being rotated, this method is build to search through
    multiple JWK that could be in the set.

    As JWKS are being cached, if a JWK cannot be found, cached
    JWKS is purged and a new JWKS is fetched from Auth0. The
    fresh JWKS is then searched again for the needed key.

    Returns the key ID if found, otherwise returns None
    :param jwt_string: The JWT token as a string
    :return: str
    '''

    try:
        # Get the JWK
        jwks = get_public_keys_from_auth0(refresh=False)

        # Decode the JWTs header component
        unverified_header = jwt.get_unverified_header(str(jwt_string))

        # Check the JWK for the key the JWT was signed with
        rsa_key = get_rsa_from_jwks(jwks, unverified_header['kid'])
        if not rsa_key:
            logger.debug('No matching key found in JWKS, refreshing')
            logger.debug('Unverified JWT key id: {}'.format(unverified_header['kid']))
            logger.debug('Cached JWK keys: {}'.format([jwk['kid'] for jwk in jwks['keys']]))

            # No match found, refresh the jwks
            jwks = get_public_keys_from_auth0(refresh=True)
            logger.debug('Refreshed JWK keys: {}'.format([jwk['kid'] for jwk in jwks['keys']]))

            # Try it again
            rsa_key = get_rsa_from_jwks(jwks, unverified_header['kid'])
            if not rsa_key:
                logger.warning('No matching key found despite refresh, failing: {}'.format(unverified_header.get('kid')))

        return rsa_key

    except jwt.exceptions.DecodeError as e:
        logger.debug('Invalid JWT used: {}'.format(e))

    except KeyError as e:
        logger.exception('Comparing public key failed: {}'.format(e), exc_info=True,
                         extra={'jwt': jwt_string, 'jwks': jwks})

    except Exception as e:
        logger.exception('Unexpected public key error: {}'.format(e), exc_info=True,
                         extra={'jwt': jwt_string, 'jwks': jwks})

    return None


def get_rsa_from_jwks(jwks, jwt_kid):
    '''
    Searches the JWKS for the signing key used
    for the JWT. Returns a dict of the JWK
    properties if found, None otherwise.
    :param jwks: The set of JWKs from Auth0
    :param jwt_kid: The key ID of the signing key
    :return: dict
    '''
    # Build the dict containing rsa values
    for key in jwks["keys"]:
        if key["kid"] == jwt_kid:
            rsa_key = {
                "kty": key["kty"],
                "kid": key["kid"],
                "use": key["use"],
                "n": key["n"],
                "e": key["e"]
            }

            return rsa_key

    # No matching key found, must refresh JWT keys
    return None


def validate_rs256_jwt(jwt_string):
    '''
    Verifies the given RS256 JWT. Returns the payload
    if verified, otherwise returns None.
    :param jwt_string: JWT as a string
    :return: dict
    '''

    rsa_pub_key = retrieve_public_key(jwt_string)
    payload = None

    if rsa_pub_key:
        jwk_key = jwk.JWK(**rsa_pub_key)

        # Determine which Auth0 Client ID (aud) this JWT pertains to.
        try:
            auth0_client_id = str(jwt.decode(jwt_string, verify=False)['aud'])
        except Exception as e:
            logger.exception('Failed to get the aud from jwt payload: {}'.format(e), exc_info=True,
                             extra={'jwt': jwt_string})
            return None

        # Check that the Client ID is in the allowed list of Auth0 Client IDs for this application
        allowed_auth0_client_id_list = settings.AUTH0_CLIENT_ID_LIST
        if auth0_client_id not in allowed_auth0_client_id_list:
            logger.warning('Auth0 client not allowed: {}'.format(auth0_client_id),
                           extra={'jwt': jwt_string})
            return None

        # Attempt to validate the JWT (Checks both expiry and signature)
        try:
            payload = jwt.decode(jwt_string,
                                 jwk_key.export_to_pem(private_key=False),
                                 algorithms=['RS256'],
                                 leeway=120,
                                 audience=auth0_client_id)
            return payload

        except jwt.ExpiredSignatureError:
            logger.debug("JWT Expired.")

        except jwt.InvalidTokenError:
            logger.debug("Invalid JWT Token.")

        except Exception as e:
            logger.exception('Unexpected validation error: {}'.format(e), exc_info=True,
                             extra={'jwt': jwt_string, 'auth0_client_id': auth0_client_id})

    return None


def jwt_login(request, jwt_payload):
    """
    The user has a valid JWT but needs to log into this app. Do so here and return the status.
    :param request:
    :param jwt_payload: String form of the JWT.
    :return:
    """

    logger.debug("Logging user in via JWT. Is Authenticated? " + str(request.user.is_authenticated))

    request.session['profile'] = jwt_payload

    user = django_auth.authenticate(**jwt_payload)

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
    login_url = furl(settings.AUTHENTICATION_LOGIN_URL)
    login_url.query.params.add('next', request.build_absolute_uri())

    # Check for branding
    if hasattr(settings, 'SCIAUTH_BRANDING'):
        logger.debug('SciAuth branding passed')

        # Encode it and pass it
        branding = base64.urlsafe_b64encode(json.dumps(settings.SCIAUTH_BRANDING).encode('utf-8')).decode('utf-8')
        login_url.query.params.add('branding', branding)

    # Set the URL and purge cookies
    response = redirect(login_url.url)
    response.delete_cookie('DBMI_JWT', domain=settings.COOKIE_DOMAIN)
    logger.debug('Redirecting to: {}'.format(login_url.url))

    return response


class Auth0Authentication(object):

    def authenticate(self, request, **token_dictionary):
        logger.debug("Authenticate User: {}/{}".format(token_dictionary.get('sub'), token_dictionary.get('email')))

        try:
            user = User.objects.get(username=token_dictionary["email"])
        except User.DoesNotExist:
            logger.debug("User not found, creating: {}".format(token_dictionary.get('email')))

            user = User(username=token_dictionary["email"], email=token_dictionary["email"])
            user.save()
        return user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
