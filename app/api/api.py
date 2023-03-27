from django.http import Http404
from django.contrib.auth.models import User
from django.db.models import Q
from django.shortcuts import get_object_or_404

from datetime import datetime, timedelta
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.views import APIView
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework import authentication, permissions
from rest_framework import exceptions
from rest_framework.decorators import action
from dbmi_client import authz
from dbmi_client.authn import DBMIModelUser
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiParameter, extend_schema_view

from api.scheme import JWTScheme
from projects.models import DataProject, HostedFile
from api.serializers import (
    DataProjectSerializer,
    HostedFileSerializer,
    HostedFileDownloadSerializer,
)
from hypatio.file_services import get_download_url


class HostedFilePermission(permissions.BasePermission):
    """
    This BasePermission subclass ensures the requesting user has adequate
    permissions on the DataProject to which the HostedFile belongs.
    """

    READ_PERMISSIONS = ["VIEW", "MANAGE"]
    WRITE_PERMISSIONS = ["MANAGE"]

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        # Check Participant objects first
        if request.user.participant_set.filter(
                project=view.project,
                permission__in=self.READ_PERMISSIONS):
            return True

        if authz.has_a_permission(
                request=request,
                email=request.user.email,
                item=f"Hypatio.{view.project.project_key}",
                permissions=self.READ_PERMISSIONS,
                check_parents=True):
            return True


class DataProjectViewSet(viewsets.ReadOnlyModelViewSet):
    """
    A view for listing or retrieving projects.
    """
    authentication_classes = [DBMIModelUser]
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    queryset = DataProject.objects.filter(visible=True)
    serializer_class = DataProjectSerializer
    lookup_field = "id"


# Define parameters schema for detail views
detail_parameters = [
    OpenApiParameter(
        "project_id",
        type=int,
        description="The unique ID of the project containing the file(s).",
        location=OpenApiParameter.PATH,
        required=True,
    ),
]

@extend_schema_view(
    list=extend_schema(
        parameters=detail_parameters,
    ),
    retrieve=extend_schema(
        parameters=detail_parameters,
    ),
    download=extend_schema(
        description="A view for downloading a project's files.",
        parameters=detail_parameters,
        responses=HostedFileDownloadSerializer,
    ),
)
class HostedFileViewSet(viewsets.ReadOnlyModelViewSet):
    """
    A view for listing or retrieving a projects's files.
    """
    authentication_classes = [DBMIModelUser]
    permission_classes = [permissions.IsAuthenticated, HostedFilePermission]
    filter_backends = [DjangoFilterBackend]
    queryset = HostedFile.objects.filter(enabled=True)
    serializer_class = HostedFileSerializer
    lookup_field = "id"
    project_lookup = "project_id"

    def get_queryset(self):
        return HostedFile.objects.filter(
            project=self.kwargs[self.project_lookup],
            enabled=True,
        )

    def initial(self, request, *args, **kwargs):
        print(kwargs)
        self.project = get_object_or_404(DataProject.objects.all(), pk=kwargs[self.project_lookup])
        return super(HostedFileViewSet, self).initial(request, args, kwargs)

    @action(detail=True, methods=['get'])
    def download(self, request, project_id, id):
        serializer = HostedFileDownloadSerializer(self.get_object())
        return Response(serializer.data)
