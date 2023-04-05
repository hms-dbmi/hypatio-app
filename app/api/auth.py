from rest_framework import permissions
from dbmi_client import authz

from projects.models import DataProject

import logging
logger = logging.getLogger(__name__)


class DataProjectPermission(permissions.BasePermission):
    message = 'Access to data project is prohibited.'

    # Permission strings for the Data Portal
    READ_PERMISSIONS = ["VIEW", "MANAGE"]
    WRITE_PERMISSIONS = ["MANAGE"]

    def has_read_permission(self, request, project):
        """
        Returns whether the requesting user has a read permission on the passed
        project or not.

        :param request: The current request
        :type request: HttpRequest
        :param project: The DataProject the requestor is attempting to read
        :type project: DataProject
        """
        # Check Participant objects first
        if request.user.participant_set.filter(
                project=project,
                permission__in=self.READ_PERMISSIONS):
            return True

        if authz.has_a_permission(
                request=request,
                email=request.user.email,
                item=f"Hypatio.{project.project_key}",
                permissions=self.READ_PERMISSIONS,
                check_parents=True):
            return True

        return False

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

    def has_object_permission(self, request, view, obj):

        # Ensure user has permission on the given project.

        # Get the project
        try:
            project = DataProject.objects.get(pk=obj)
        except DataProject.DoesNotExist:
            logger.error(f"DataProject does not exist for PK: '{obj}'")
            return False

        # Check Participant objects first
        if self.has_read_permission(request, project):
            return True

        logger.debug(f"Access denied on '{obj}' for: {request.user.email}")
        return False


class HostedFilePermission(DataProjectPermission):
    """
    This BasePermission subclass ensures the requesting user has adequate
    permissions on the DataProject to which the HostedFile belongs.
    """
    message = 'Access to file is prohibited.'

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        # Check Participant objects first
        if self.has_read_permission(request, view.project):
            return True

    def has_object_permission(self, request, view, obj):
        return True
