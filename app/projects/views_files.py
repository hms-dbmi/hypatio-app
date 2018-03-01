import logging
import boto3
import botocore

from django.conf import settings
from django.http import StreamingHttpResponse
from django.http import HttpResponse
from django.shortcuts import redirect
from django.shortcuts import get_object_or_404
from django.core.files.base import ContentFile

from hypatio.sciauthz_services import SciAuthZ
from hypatio.file_services import get_download_url

from .models import HostedFile
from .models import HostedFileDownload

from pyauth0jwt.auth0authenticate import user_auth_and_jwt

logger = logging.getLogger(__name__)

@user_auth_and_jwt
def download_dataset(request):
    logger.debug("[views_files][download_dataset] - Attempting file download.")

    # Check Permissions in SciAuthZ
    user_jwt = request.COOKIES.get("DBMI_JWT", None)
    sciauthz = SciAuthZ(settings.AUTHZ_BASE, user_jwt, request.user.email)

    if not sciauthz.user_has_single_permission("n2c2-t1", "VIEW"):
        logger.debug("[views_files][download_dataset] - No Access for user " + request.user.email)
        return HttpResponse(403)

    file_id = request.GET.get("file_id")
    file_to_download = get_object_or_404(HostedFile, id=file_id)

    # Save a record of this person downloading this file
    HostedFileDownload.objects.create(user=request.user, hosted_file=file_to_download)

    s3 = boto3.resource('s3')

    s3_filename = file_to_download.file_location + "/" + file_to_download.file_name
    logger.debug("[views_files][download_dataset] - User " + request.user.email + " is downloading file " + s3_filename + " from bucket " + settings.S3_BUCKET + ".")

    download_url = get_download_url(s3_filename)

    response = redirect(download_url)
    response['Content-Disposition'] = 'attachment'
    response['filename'] = file_to_download.file_name

    return response