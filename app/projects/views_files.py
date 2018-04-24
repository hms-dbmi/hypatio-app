import json
import logging
import os
import shutil
import zipfile
import uuid

from copy import copy
from datetime import datetime

import requests

from django.conf import settings
from django.core import exceptions
from django.http import HttpResponse
from django.http import JsonResponse
from django.http import QueryDict
from django.shortcuts import redirect
from django.shortcuts import get_object_or_404

from pyauth0jwt.auth0authenticate import user_auth_and_jwt

from hypatio.sciauthz_services import SciAuthZ
from hypatio.file_services import get_download_url
from hypatio import file_services as fileservice

from .models import DataProject
from .models import HostedFile
from .models import HostedFileDownload
from .models import ParticipantSubmission
from .models import TeamSubmissionsDownload
from .models import Participant
from .models import Team

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
def download_team_submissions(request):
    """
    Handles downloads of participant submission files. Checks that the requesting user
    has proper permissions to access this file. Downloads all of the team's submissions
    into one zip file, with each submission in it's own zip file containing a json file
    with metadata about the upload.
    """
    logger.debug('download_team_submissions: {}'.format(request.method))

    if request.method == "GET":

        project_key = request.GET.get("project_key", "")
        team_leader_email = request.GET.get("team", "")

        if project_key == "" or team_leader_email == "":
            return HttpResponse("Not all parameters provided.", status=404)

        # Check Permissions in SciAuthZ
        user_jwt = request.COOKIES.get("DBMI_JWT", None)
        sciauthz = SciAuthZ(settings.AUTHZ_BASE, user_jwt, request.user.email)
        is_manager = sciauthz.user_has_manage_permission(request, project_key)

        if not is_manager:
            logger.debug("[views_files][download_team_submissions] - No Access for user " + request.user.email)
            return HttpResponse("You do not have access to download this file.", status=403)

        project = get_object_or_404(DataProject, project_key=project_key)
        team = get_object_or_404(Team, data_project=project, team_leader__email=team_leader_email)
        team_participants = team.participant_set.all()

        # Get all of the participant submission records belonging to this team, ordered by upload date
        team_submissions = ParticipantSubmission.objects.filter(
            participant__in=team_participants
        ).order_by('upload_date')

        logger.debug('Building a zip file containing the {submission_count} submissions from team {team}.'.format(
            submission_count=team_submissions.count(),
            team=team_leader_email
        ))

        # Save a record of this person downloading this team's submissions file
        download_record = TeamSubmissionsDownload.objects.create(
            user=request.user,
            team=team
        )

        # Once the record is created and a pk assigned, update with the specific submissions referenced
        download_record.participant_submissions = team_submissions
        download_record.save()

        # Create a dictory to hold the zipped submissions using a guid to keep it isolated from other requests
        zipped_submissions_directory = "/tmp/" + str(uuid.uuid4())
        if not os.path.exists(zipped_submissions_directory):
            os.makedirs(zipped_submissions_directory)

        # A list of the file paths for each Hypatio-generated team submission zip file
        zipped_submission_filepaths = []

        for i, submission in enumerate(team_submissions):
            submission_number = i + 1
            submission_date_string = datetime.strftime(submission.upload_date, "%Y%m%d_%H%M")

            # Create a working directory to hold the files specific to this submission that need to be zipped together
            working_directory = "/tmp/" + str(uuid.uuid4())
            if not os.path.exists(working_directory):
                os.makedirs(working_directory)

            # Create a json file with the submission info string
            info_file_name = "submission_info.json"
            with open(working_directory + "/" + info_file_name, mode="w") as f:
                f.write(submission.submission_info)

            # Get the submission file's byte contents from S3
            submission_file_download_url = fileservice.get_fileservice_download_url(request, submission.uuid)
            submission_file_request = requests.get(submission_file_download_url)

            # Write the bytes to a zip file
            submission_file_name = "submission_file.zip"
            if submission_file_request.status_code == 200:
                with open(working_directory + "/" + submission_file_name, mode="wb") as f:
                    f.write(submission_file_request.content)
            else:
                logger.error("[views_files][download_team_submissions] - Participant submission {uuid} file could not be pulled from S3.".format(
                    uuid=submission.uuid
                ))
                return HttpResponse("Error getting files", status=404)

            # Create the zip file and add the files to it
            zip_file_path = zipped_submissions_directory + "/submission_" + str(submission_number) + "_" + submission_date_string + ".zip"
            with zipfile.ZipFile(zip_file_path, mode="w") as zf:
                zf.write(working_directory + "/" + info_file_name, arcname=info_file_name)
                zf.write(working_directory + "/" + submission_file_name, arcname=submission_file_name)

            # Add the zipfile to the list of zip files
            zipped_submission_filepaths.append(zip_file_path)

            # Delete the working directory
            shutil.rmtree(working_directory)

        # Create a directory to store the encompassing zip file using a guid to keep it isolated from other requests
        final_zip_file_directory = "/tmp/" + str(uuid.uuid4())
        if not os.path.exists(final_zip_file_directory):
            os.makedirs(final_zip_file_directory)

        # Create the encompassing zip file
        final_zip_file_name = project_key + "_submissions_" + team_leader_email.replace('@', '-at-') + ".zip"
        final_zip_file_path = os.path.join(final_zip_file_directory, final_zip_file_name)
        with zipfile.ZipFile(final_zip_file_path, mode="w") as zf:
            for submission_zip in zipped_submission_filepaths:
                zf.write(submission_zip, arcname=os.path.basename(submission_zip))

        # Prepare the zip file to be served
        final_zip_file = open(final_zip_file_path, 'rb')
        response = HttpResponse(final_zip_file, content_type='application/force-download')
        response['Content-Disposition'] = 'attachment; filename="%s"' % final_zip_file_name

        # Delete all the zip files from disk storage
        shutil.rmtree(final_zip_file_directory)
        shutil.rmtree(zipped_submissions_directory)

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

        if filename.split(".")[-1] != "zip":
            logger.error('Not a zip file.')
            return HttpResponse("Only .zip files are accepted", status=400)

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
            submission_info['submitted_by'] = request.user.email
            submission_info['team_leader'] = participant.team.team_leader.email
            submission_info_json = json.dumps(submission_info, indent=4)

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
