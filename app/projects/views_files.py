import logging
import boto3

from django.conf import settings
from django.http import StreamingHttpResponse
from django.http import HttpResponse

from hypatio.sciauthz_services import SciAuthZ

from .models import HostedFile, HostedFileDownload

from pyauth0jwt.auth0authenticate import user_auth_and_jwt

log = logging.getLogger(__name__)


@user_auth_and_jwt
def download_dataset(request):
    log.debug("[views_files][download_dataset] - Attempting file download.")

    # Check Permissions in SciAuthZ
    user_jwt = request.COOKIES.get("DBMI_JWT", None)
    sciauthz = SciAuthZ(settings.AUTHZ_BASE, user_jwt, request.user.email)

    if not sciauthz.user_has_single_permission("n2c2-t1", "VIEW"):
        log.debug("[views_files][download_dataset] - No Access for user.")
        return HttpResponse(403)

    file_id = request.GET.get("file_id")
    file_to_download = HostedFile.objects.get(id=file_id)

    s3 = boto3.client('s3')

    HostedFileDownload.objects.create(user=request.user, hosted_file= file_to_download)

    with open('filename', 'wb') as data:
        s3.download_fileobj(settings.HYPATIO_S3_BUCKET, file_to_download.file_location, data)
        return data

    # with open('filename', 'wb') as data:
     #   return StreamingHttpResponse(streaming_content=s3.download_fileobj(settings.HYPATIO_S3_BUCKET, file_to_download.file_location, data))



