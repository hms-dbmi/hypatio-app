import logging

from django.shortcuts import get_object_or_404
from django.conf import settings
from django.http import QueryDict
from django.core import exceptions
from django.shortcuts import redirect
from django.http import JsonResponse, HttpResponse
from pyauth0jwt.auth0authenticate import user_auth_and_jwt
from rest_framework.exceptions import ValidationError

from hypatio.sciauthz_services import SciAuthZ
from hypatio.file_services import get_download_url
from hypatio import file_services as fileservice

from .models import HostedFile
from .models import HostedFileDownload
from .models import ParticipantSubmission
from .models import Participant

logger = logging.getLogger(__name__)


@user_auth_and_jwt
def download_dataset(request):
    logger.debug("[views_files][download_dataset] - Attempting file download.")

    # Check Permissions in SciAuthZ
    user_jwt = request.COOKIES.get("DBMI_JWT", None)
    sciauthz = SciAuthZ(settings.AUTHZ_BASE, user_jwt, request.user.email)

    if not sciauthz.user_has_single_permission("n2c2-t1", "VIEW"):
        logger.debug("[views_files][download_dataset] - No Access for user " + request.user.email)
        return HttpResponse("403 Forbidden. You do not have access to download this file.")

    file_id = request.GET.get("file_id")
    file_to_download = get_object_or_404(HostedFile, id=file_id)

    # Save a record of this person downloading this file
    HostedFileDownload.objects.create(user=request.user, hosted_file=file_to_download)

    s3_filename = file_to_download.file_location + "/" + file_to_download.file_name
    logger.debug("[views_files][download_dataset] - User " + request.user.email + " is downloading file " + s3_filename + " from bucket " + settings.S3_BUCKET + ".")

    download_url = get_download_url(s3_filename)

    response = redirect(download_url)
    response['Content-Disposition'] = 'attachment'
    response['filename'] = file_to_download.file_name

    return response


@user_auth_and_jwt
def upload_dataset(request):
    logger.debug('upload_dataset: {}'.format(request.method))

    # Check method
    if request.method == 'POST':
        logger.debug('post')

        # Check user permissions
        # TODO: Finish this

        # Assembles the form and run validation.
        filename = request.POST.get('filename')
        project = request.POST.get('project')
        if not filename or not project:
            logger.error('No filename or no project!')
            return HttpResponse('Filename and project are required', status=400)

        # Prepare the metadata
        # TODO: Finish this
        metadata = {
            'project': project,
            'uploader': request.user.email,
            'type': 'project_submission',
            'app': 'hypatio',
        }

        # Get the file link
        uuid, response = fileservice.create_file(request, filename, metadata)

        # Get the needed bits.
        post = response['post']
        location = response['locationid']

        # Form the data for the File object.
        file = {'uuid': uuid, 'location': location, 'filename': filename}

        logger.debug('File: {}'.format(file))

        # Build the response
        response = {
            'post': post,
            'file': file,
        }

        logger.debug('Response: {}'.format(post))

        return JsonResponse(data=response)

    elif request.method == 'PATCH':
        logger.debug('patch')

        # Get the data
        data = QueryDict(request.body)

        logger.debug('Data: {}'.format(data))

        try:
            # Get the participant
            participant = Participant.objects.get(user=request.user)

            # Create the object and save UUID and location for future downloads
            ParticipantSubmission.objects.create(
                participant=participant,
                uuid=data['uuid'],
                location=data['location'])

            # Make the request to FileService.
            if not fileservice.uploaded_file(request, data['uuid'], data['location']):
                logger.error('[participants][FilesView][post] FileService uploadCompleted failed!')
            else:
                logger.debug('FileService updated of file upload')

            return HttpResponse(status=200)

        except exceptions.ObjectDoesNotExist as e:
            logger.exception(e)

            return HttpResponse(status=404)

        except Exception as e:
            logger.exception(e)

            return HttpResponse(status=500)
    else:

        return HttpResponse("Invalid method", status=403)



