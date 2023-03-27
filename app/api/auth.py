from rest_framework import permissions
from django.core.exceptions import ObjectDoesNotExist

from projects.models import DataProject
from projects.models import Participant

import logging
logger = logging.getLogger(__name__)


class DataProjectPermission(permissions.BasePermission):
    message = 'Access to data project is prohibited.'

    def has_object_permission(self, request, view, obj):

        # Ensure user has permission on the given project.

        # Get the project
        try:
            project = DataProject.objects.get(project_key=obj)
        except ObjectDoesNotExist:
            logger.debug(f"No project found for key: {obj}")
            return False

        # If the project doesn't require authorization, grant access
        if not project.requires_authorization:
            logger.debug(f"No auth for project, access granted for: {obj}{request.user.email}")
            return True

        # Get their permission for this project
        try:
            participant = Participant.objects.get(user=request.user, project=project)

            # Check permission
            if participant.permission == "VIEW":
                logger.debug(f"Access granted for: {obj}{request.user.email}")
                return True

        except ObjectDoesNotExist:
            logger.debug(f"Participant does not exist for: {obj}/{request.user.email}", extra={
                "request": request, "project": obj, "user": request.user,
            })

        logger.debug(f"Access denied for: {obj}{request.user.email}")
        return False
