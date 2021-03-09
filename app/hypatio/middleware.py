from django.conf import settings
from dbmi_client import environment

import logging
logger = logging.getLogger(__name__)


class XRobotsTagMiddleware(object):
    """Adds X-Robots-Tag Based on environment"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if hasattr(settings, "X_ROBOTS_TAG") and settings.X_ROBOTS_TAG:
            response["X-Robots-Tag"] = ",".join(settings.X_ROBOTS_TAG)
        elif environment.get_str("DBMI_ENV") != "prod":
            response["X-Robots-Tag"] = "noindex,nofollow"

        return response
