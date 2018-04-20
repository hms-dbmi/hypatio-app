import logging
import json
from copy import copy

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
from .models import ParticipantSubmissionDownload
from .models import Participant

logger = logging.getLogger(__name__)


@user_auth_and_jwt
def download_dataset(request):
    """
    Handles downloads for project level files. Checks that the requesting user
    has view permissions on the given project before allowing a download.
    """

    logger.debug("[views_files][download_dataset] - Attempting file download.")

    # Check Permissions in SciAuthZ
    user_jwt = request.COOKIES.get("DBMI_JWT", None)
    sciauthz = SciAuthZ(settings.AUTHZ_BASE, user_jwt, request.user.email)

    if not sciauthz.user_has_single_permission("n2c2-t1", "VIEW"):
        logger.debug("[views_files][download_dataset] - No Access for user " + request.user.email)
        return HttpResponse("You do not have access to download this file.", status=403)

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
def download_participantsubmission_file(request):
    """
    Handles downloads of participant submission files. Checks that the requesting user
    has proper permissions to access this file.
    """
    logger.debug('download_participantsubmission_file: {}'.format(request.method))

    if request.method == "GET":

        project_key = request.GET.get("project_key", "")
        fileservice_uuid = request.GET.get("uuid", "")

        # Check Permissions in SciAuthZ
        user_jwt = request.COOKIES.get("DBMI_JWT", None)
        sciauthz = SciAuthZ(settings.AUTHZ_BASE, user_jwt, request.user.email)
        is_manager = sciauthz.user_has_manage_permission(request, project_key)

        if not is_manager:
            logger.debug("[views_files][download_participantsubmission_file] - No Access for user " + request.user.email)
            return HttpResponse("You do not have access to download this file.", status=403)

        # Save a record of this person downloading this file
        participant_submission = ParticipantSubmission.objects.get(uuid=fileservice_uuid)
        ParticipantSubmissionDownload.objects.create(user=request.user, participant_submission=participant_submission)

        url = fileservice.download_file(request, fileservice_uuid)

        response = redirect(url)
        response['Content-Disposition'] = 'attachment'

        return response

@user_auth_and_jwt
def upload_participantsubmission_file(request):
    """
    On a POST, send metadata about the user's file to fileservice to get back an S3 upload link.
    On a PATCH, check to see that the file successfully was uploaded to S3 and then create a new
    ParticipantSubmission record.
    """
    logger.debug('upload_participantsubmission_file: {}'.format(request.method))

    if request.method == 'POST':
        logger.debug('post')

        # Check that user has permissions to be submitting files for this project.
        user_jwt = request.COOKIES.get("DBMI_JWT", None)
        sciauthz = SciAuthZ(settings.AUTHZ_BASE, user_jwt, request.user.email)

        if not sciauthz.user_has_single_permission("n2c2-t1", "VIEW"):
            logger.debug("[views_files][upload_participantsubmission_file] - No Access for user " + request.user.email)
            return HttpResponse("You do not have access to upload this file.", status=403)

        # Assembles the form and runs validation.
        filename = request.POST.get('filename')
        project = request.POST.get('project')
        if not filename or not project:
            logger.error('No filename or no project!')
            return HttpResponse('Filename and project are required', status=400)

        # Prepare the metadata.
        metadata = {
            'project': project,
            'uploader': request.user.email,
            'type': 'project_submission',
            'app': 'hypatio',
        }

        # Create a new record in fileservice for this file and get back information on where it should live in S3.
        uuid, response = fileservice.create_file(request, filename, metadata)
        post = response['post']
        location = response['locationid']

        # Form the data for the File object.
        file = {'uuid': uuid, 'location': location, 'filename': filename}
        logger.debug('File: {}'.format(file))

        response = {
            'post': post,
            'file': file,
        }
        logger.debug('Response: {}'.format(post))

        return JsonResponse(data=response)

    elif request.method == 'PATCH':
        logger.debug('patch')

        # Get the data.
        data = QueryDict(request.body)
        logger.debug('Data: {}'.format(data))

        try:
            # Get the participant.
            participant = Participant.objects.get(user=request.user)

            # Prepare a json that holds information about the file and the original submission form.
            # This is used later as included metadata when downloading the participant's submission.
            # Remove a few unnecessary fields.
            submission_info = copy(data)
            del submission_info['csrfmiddlewaretoken']
            del submission_info['location']
            submission_info_json = json.dumps(submission_info)

            # Create the object and save UUID and location for future downloads.
            ParticipantSubmission.objects.create(
                participant=participant,
                uuid=data['uuid'],
                location=data['location'],
                submission_info=submission_info_json
            )

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
