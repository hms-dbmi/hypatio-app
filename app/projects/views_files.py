import logging
import boto3
import botocore

from django.conf import settings
from django.http import StreamingHttpResponse
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.core.files.base import ContentFile

from hypatio.sciauthz_services import SciAuthZ

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

    filename_in_s3 = file_to_download.file_location + "/" + file_to_download.file_name
    logger.debug("[views_files][download_dataset] - Attempting to download file " + filename_in_s3 + " from bucket " + settings.HYPATIO_S3_BUCKET)

    # TODO: Plan A: redirect user's page to the S3 link to trigger the download -- will need to change the jquery code in project_compete.html
    # TODO: Plan B: return the S3 link to the project_compete.html page -- the jquery there can handle this now

    # with open('filename', 'wb') as data:
    #     try:
    #         s3.Bucket(settings.HYPATIO_S3_BUCKET).download_file(filename_in_s3, data)
    #     except botocore.exceptions.ClientError as e:
    #         if e.response['Error']['Code'] == "404":
    #             logger.debug('[views_files][download_dataset] - File does not exist in S3.')
    #             return HttpResponse(404)
    #         else:
    #             logger.debug('[views_files][download_dataset] - Error ' + e)
    #             return HttpResponse(500)
        
    # with open('filename', 'wb') as data:
    #     s3.download_fileobj(settings.HYPATIO_S3_BUCKET, file_to_download.file_location, data)
    #     return data

    # with open('filename', 'wb') as data:
     #   return StreamingHttpResponse(streaming_content=s3.download_fileobj(settings.HYPATIO_S3_BUCKET, file_to_download.file_location, data))

    return "S3 LINK HERE?"