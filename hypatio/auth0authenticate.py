from django.contrib.auth.models import User
import logging
logger = logging.getLogger(__name__)


class Auth0Authentication(object):

    def authenticate(self, **token_dictionary):
        logger.debug("Attempting to Authenticate User - " + token_dictionary["email"])

        try:
            user = User.objects.get(username=token_dictionary["email"])
        except User.DoesNotExist:
            logger.debug("User not found, creating.")

            user = User(username=token_dictionary["email"], email=token_dictionary["email"])
            user.is_staff = True
            user.is_superuser = True
            user.save()
        return user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None


