from rest_framework import serializers

from projects.models import HostedFileDownload, HostedFile, ChallengeTaskSubmission


class ChallengeTaskSubmissionSerializer(serializers.ModelSerializer):
    upload_date = serializers.SerializerMethodField(source='*')

    class Meta:
        model = ChallengeTaskSubmission
        fields = '__all__'

    def get_upload_date(self, obj):
        return obj.upload_date.isoformat()


class HostedFileSerializer(serializers.ModelSerializer):

    class Meta:
        model = HostedFile
        fields = '__all__'


class HostedFileDownloadSerializer(serializers.ModelSerializer):
    download_date = serializers.SerializerMethodField(source='*')
    user = serializers.SerializerMethodField(source='*')

    class Meta:
        model = HostedFileDownload
        fields = ['user', 'download_date']

    def get_user(self, obj):
        return obj.user.email

    def get_download_date(self, obj):
        return obj.download_date.isoformat()
