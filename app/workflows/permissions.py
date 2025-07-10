from http import HTTPMethod

from rest_framework import permissions
from rest_framework import request
from dbmi_client import authz

from projects.models import DataProjectWorkflow


class BaseWorkflowsPermission(metaclass=permissions.BasePermissionMetaclass):
    """
    A base class from which all permission classes should inherit.
    """

    def has_permission(self, request, view):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        return request.user.is_staff


class ReadAndWriteOnly(BaseWorkflowsPermission):
    """
    A base class from which all permission classes should inherit.
    """

    def has_permission(self, request, view):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        return request.method != HTTPMethod.DELETE

    def has_object_permission(self, request, view, obj):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        return request.method != HTTPMethod.DELETE


class ReadOnly(BaseWorkflowsPermission):
    """
    A base class from which all permission classes should inherit.
    """

    def has_permission(self, request, view):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        return request.method in [HTTPMethod.HEAD, HTTPMethod.OPTIONS, HTTPMethod.GET, ]

    def has_object_permission(self, request, view, obj):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        return request.method in [HTTPMethod.HEAD, HTTPMethod.OPTIONS, HTTPMethod.GET, ]


class IsOwner(BaseWorkflowsPermission):
    """
    A base class from which all permission classes should inherit.
    """
    def has_object_permission(self, request, view, obj):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        # Check if owner, but not in administration
        if request.user == obj.user and not view.is_administration:
            return True

        return False


class IsAdministrator(BaseWorkflowsPermission):
    """
    A base class from which all permission classes should inherit.
    """
    def has_object_permission(self, request, view, obj):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        # Check if staff
        if request.user.is_staff:
            return True

        # Check if linked to a DataProject
        try:
            # Check if admin
            data_project = DataProjectWorkflow.objects.get(workflow=obj.workflow).data_project
            if authz.has_permission(
                request=request,
                email=request.user.email,
                item=f"hypatio.{data_project.project_key}",
                permission="MANAGE",
                check_parents=True,
                ):
                return True

        except DataProjectWorkflow.DoesNotExist:
            pass

        return False


class IsWorkflowStateOwnerOrDataProjectAdministrator(BaseWorkflowsPermission):
    """
    A base class from which all permission classes should inherit.
    """
    def has_object_permission(self, request, view, obj):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        # Check if staff
        if request.user.is_staff:
            return True

        # Check if owner, but not in administration
        if request.user == obj.user and not view.is_administration:
            return True

        # Check if linked to a DataProject
        try:
            # Check if admin
            data_project = DataProjectWorkflow.objects.get(workflow=obj.workflow).data_project
            if authz.has_permission(
                request=request,
                email=request.user.email,
                item=f"hypatio.{data_project.project_key}",
                permission="MANAGE",
                check_parents=True,
                ):
                return True

        except DataProjectWorkflow.DoesNotExist:
            pass

        return False


class IsStepStateOwnerOrDataProjectAdministrator(BaseWorkflowsPermission):
    """
    A base class from which all permission classes should inherit.
    """
    def has_object_permission(self, request, view, obj):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        # Check if staff
        if request.user.is_staff:
            print(f"[{self.__class__.__name__}] Is staff")
            return True

        # Check if owner but not administration
        if request.user == obj.user and not view.is_administration:
            print(f"[{self.__class__.__name__}] Is owner")
            return True

        # Check if linked to a DataProject
        try:
            # Check if admin
            data_project = DataProjectWorkflow.objects.get(workflow=obj.step.workflow).data_project
            if authz.has_permission(
                request=request,
                email=request.user.email,
                item=f"hypatio.{data_project.project_key}",
                permission="MANAGE",
                check_parents=True
                ):
                print(f"[{self.__class__.__name__}] Is Data Project administrator")
                return True

        except DataProjectWorkflow.DoesNotExist:
            pass

        return False
