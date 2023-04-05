from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework import mixins
from rest_framework.response import Response
from rest_framework import authentication
from rest_framework import permissions
from rest_framework.decorators import action
from dbmi_client.authn import DBMIModelUser
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiParameter, extend_schema_view

from projects.models import DataProject, HostedFile
from api.serializers import (
    DataProjectSerializer,
    HostedFileSerializer,
    HostedFileDownloadSerializer,
)
from api.auth import HostedFilePermission

import logging
logger = logging.getLogger(__name__)


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
