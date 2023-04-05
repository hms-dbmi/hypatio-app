from rest_framework import serializers
from datetime import datetime, timedelta

from drf_spectacular.utils import extend_schema_field
from drf_spectacular.types import OpenApiTypes

from projects.models import DataProject
from projects.models import HostedFile
from hypatio.file_services import get_download_url


class DataProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataProject
        fields = [
            'id', 'name', 'project_key', 'description',
            'short_description', 'created', 'modified', #TODO: 'group',
        ]

class HostedFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = HostedFile
        fields = [
            'id', 'project', 'uuid', 'long_name', 'description',
            'file_name', 'file_location', 'created', 'modified'
        ]


class HostedFileDownloadSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    expires = serializers.SerializerMethodField()

    class Meta:
        model = HostedFile
        fields = ['url', 'expires']

    @extend_schema_field(OpenApiTypes.URI)
    def get_url(self, obj):
        return get_download_url(obj.file_location + "/" + obj.file_name)

    @extend_schema_field(OpenApiTypes.DATETIME)
    def get_expires(self, obj):
        return datetime.now() + timedelta(hours=1)
