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

from projects.models import DataProject
from projects.models import HostedFile
from projects.models import HostedFileDownload
from projects.models import ChallengeTask
from projects.models import ChallengeTaskSubmission
from projects.models import TeamSubmissionsDownload
from projects.models import Participant
from projects.models import Team

from contact.views import email_send

from contact.views import email_send

logger = logging.getLogger(__name__)


@user_auth_and_jwt
def download_dataset(request):
    """
    Handles downloads for project level files. Checks that the requesting user
    has view permissions on the given project before allowing a download.
    """

    logger.debug("[views_files][download_dataset] - Attempting file download.")

    file_uuid = request.GET.get("file_uuid")
    file_to_download = get_object_or_404(HostedFile, uuid=file_uuid)
    project_key = file_to_download.project.project_key

    # TODO should check if this file is enabled for download
    # ...

    # Check Permissions in SciAuthZ
    user_jwt = request.COOKIES.get("DBMI_JWT", None)
    sciauthz = SciAuthZ(settings.AUTHZ_BASE, user_jwt, request.user.email)

    if not sciauthz.user_has_single_permission(project_key, "VIEW"):
        logger.debug("[views_files][download_dataset] - No Access for user " + request.user.email)
        return HttpResponse("You do not have access to download this file.", status=403)

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
        is_manager = sciauthz.user_has_manage_permission(project_key)

        if not is_manager:
            logger.debug("[views_files][download_team_submissions] - No Access for user " + request.user.email)
            return HttpResponse("You do not have access to download this file.", status=403)

        project = get_object_or_404(DataProject, project_key=project_key)
        team = get_object_or_404(Team, data_project=project, team_leader__email=team_leader_email)
        team_participants = team.participant_set.all()

        logger.debug('Building a zip file containing the submissions from team {team}.'.format(
            team=team_leader_email
        ))

        # Get all of the participant submission records belonging to this team, ordered by upload date
        team_submissions = team.get_submissions().order_by('upload_date')

        # Save a record of this person downloading this team's submissions file
        download_record = TeamSubmissionsDownload.objects.create(
            user=request.user,
            team=team
        )

        # Once the record is created and a pk assigned, update with the specific submissions referenced
        download_record.participant_submissions = team_submissions
        download_record.save()

        # Create a dictory to hold the zipped submissions using a guid to keep it isolated from other requests
        zipped_submissions_directory = "/tmp/zipped_submissions-" + str(uuid.uuid4())
        if not os.path.exists(zipped_submissions_directory):
            os.makedirs(zipped_submissions_directory)

        # A list of file paths to each task's zip file
        zipped_tasks_filepath = []

        # Create subdirectories for each challenge task
        for task in project.challengetask_set.all():

            # A list of file paths to each submission zip file for this task
            zipped_task_submission_filepaths = []

            # Get the submissions for this task submitted by the team.
            submissions = ChallengeTaskSubmission.objects.filter(
                challenge_task=task,
                participant__in=team.participant_set.all(),
                deleted=False
            )

            if submissions.count() > 0:

                for i, submission in enumerate(submissions):
                    submission_number = i + 1
                    submission_date_string = datetime.strftime(submission.upload_date, "%Y%m%d_%H%M")

                    # Create a working directory to hold the files specific to this submission that need to be zipped together
                    working_directory = "/tmp/working_dir-" + str(uuid.uuid4())
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
                    zip_file_path = zipped_submissions_directory + "/" + submission.challenge_task.title + "_" + str(submission_number) + "_" + submission_date_string + ".zip"
                    with zipfile.ZipFile(zip_file_path, mode="w") as zf:
                        zf.write(working_directory + "/" + info_file_name, arcname=info_file_name)
                        zf.write(working_directory + "/" + submission_file_name, arcname=submission_file_name)

                    # Add the zipfile to the list of zip files
                    zipped_task_submission_filepaths.append(zip_file_path)

                    # Delete the working directory
                    shutil.rmtree(working_directory)

                # Create a directory to store the encompassing task's zip file using a guid to keep it isolated from other requests
                task_zip_file_directory = "/tmp/task_zip-" + str(uuid.uuid4())
                if not os.path.exists(task_zip_file_directory):
                    os.makedirs(task_zip_file_directory)

                # Create the encompassing task's zip file
                task_zip_file_name = task.title + ".zip"
                task_zip_file_path = os.path.join(task_zip_file_directory, task_zip_file_name)
                with zipfile.ZipFile(task_zip_file_path, mode="w") as zf:
                    for submission_zip in zipped_task_submission_filepaths:
                        zf.write(submission_zip, arcname=os.path.basename(submission_zip))

                # Add the zipfile to the list of zip files
                zipped_tasks_filepath.append(task_zip_file_path)

        # Create a directory to store the encompassing zip file using a guid to keep it isolated from other requests
        final_zip_file_directory = "/tmp/final_zip-" + str(uuid.uuid4())
        if not os.path.exists(final_zip_file_directory):
            os.makedirs(final_zip_file_directory)

        # Combine all the zipped tasks into one file zip file
        final_zip_file_name = project_key + "_submissions_" + team_leader_email.replace('@', '-at-') + ".zip"
        final_zip_file_path = os.path.join(final_zip_file_directory, final_zip_file_name)
        with zipfile.ZipFile(final_zip_file_path, mode="w") as zf:
            for task_zip in zipped_tasks_filepath:
                zf.write(task_zip, arcname=os.path.basename(task_zip))

        # Prepare the zip file to be served
        final_zip_file = open(final_zip_file_path, 'rb')
        response = HttpResponse(final_zip_file, content_type='application/force-download')
        response['Content-Disposition'] = 'attachment; filename="%s"' % final_zip_file_name

        # Delete all the zip files from disk storage
        shutil.rmtree(final_zip_file_directory)
        shutil.rmtree(zipped_submissions_directory)
        for path in zipped_tasks_filepath:
            shutil.rmtree(os.path.dirname(path))

        return response

@user_auth_and_jwt
def upload_challengetasksubmission_file(request):
    """
    On a POST, send metadata about the user's file to fileservice to get back an S3 upload link.
    On a PATCH, check to see that the file successfully was uploaded to S3 and then create a new
    ChallengeTaskSubmission record.
    """
    logger.debug('upload_challengetasksubmission_file: {}'.format(request.method))

    if request.method == 'POST':
        logger.debug('post')

        # Assembles the form and runs validation.
        filename = request.POST.get('filename')
        project_key = request.POST.get('project_key')
        task_id = request.POST.get('task_id')

        if not filename or not project_key or not task_id:
            logger.error('No filename, project, or task!')
            return HttpResponse('Filename, project, task are required', status=400)

        # Check that user has permissions to be submitting files for this project.
        user_jwt = request.COOKIES.get("DBMI_JWT", None)
        sciauthz = SciAuthZ(settings.AUTHZ_BASE, user_jwt, request.user.email)

        if not sciauthz.user_has_single_permission(project_key, "VIEW"):
            logger.debug("[views_files][upload_challengetasksubmission_file] - No Access for user " + request.user.email)
            return HttpResponse("You do not have access to upload this file.", status=403)

        if filename.split(".")[-1] != "zip":
            logger.error('Not a zip file.')
            return HttpResponse("Only .zip files are accepted", status=400)

        try:
            task = ChallengeTask.objects.get(id=task_id)
        except exceptions.ObjectDoesNotExist:
            logger.error('Task not found with id {id}'.format(id=task_id))
            return HttpResponse('Task not found', status=400)

        # Prepare the metadata.
        metadata = {
            'project': project_key,
            'task': task.title,
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
            # Prepare a json that holds information about the file and the original submission form.
            # This is used later as included metadata when downloading the participant's submission.
            submission_info = copy(data)

            # Get the participant.
            project = get_object_or_404(DataProject, project_key=submission_info['project_key'])
            participant = get_object_or_404(Participant, user=request.user, data_challenge=project)
            team = participant.team
            task = get_object_or_404(ChallengeTask, id=submission_info['task_id'])

            # Remove a few unnecessary fields.
            del submission_info['csrfmiddlewaretoken']
            del submission_info['location']

            # Add some more fields
            submission_info['submitted_by'] = request.user.email
            submission_info['team_leader'] = participant.team.team_leader.email
            submission_info['task'] = task.title
            submission_info['submitted_on'] = datetime.strftime(datetime.now(), "%Y%m%d_%H%M")

            submission_info_json = json.dumps(submission_info, indent=4)

            # Create the object and save UUID and location for future downloads.
            ChallengeTaskSubmission.objects.create(
                challenge_task=task,
                participant=participant,
                uuid=data['uuid'],
                location=data['location'],
                submission_info=submission_info_json
            )

            # Get the submissions for this task already submitted by the team.
            total_submissions = ChallengeTaskSubmission.objects.filter(
                challenge_task=task,
                participant__in=team.participant_set.all(),
                deleted=False
            ).count()

            # Send an email notification to team members about the submission.
            emails = [member.user.email for member in team.participant_set.all()]

            context = {
                'submission_info': submission_info_json,
                'challenge': project,
                'task': task.title,
                'submitter': request.user.email,
                'max_submissions': task.max_submissions,
                'submission_count': total_submissions
            }

            try:
                subject = 'DBMI Portal - {challenge} solution submitted by your team'.format(challenge=project.project_key)

                email_success = email_send(
                    subject=subject,
                    recipients=emails,
                    email_template='email_submission_uploaded',
                    extra=context
                )
            except Exception as e:
                logger.exception(e)

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

@user_auth_and_jwt
def delete_challengetasksubmission(request):
    """
    Marks a ChallengeTaskSubmission as deleted so it will not be counted against their
    total submission count for a contest.
    """

    if request.method == 'POST':

        # Check that user has permissions to be viewing files for this project.
        user_jwt = request.COOKIES.get("DBMI_JWT", None)
        sciauthz = SciAuthZ(settings.AUTHZ_BASE, user_jwt, request.user.email)

        submission_uuid = request.POST.get('submission_uuid')
        submission = ChallengeTaskSubmission.objects.get(uuid=submission_uuid)

        project = submission.participant.data_challenge
        team = submission.participant.team

        if not sciauthz.user_has_single_permission(project.project_key, "VIEW"):
            logger.debug(
                "[views_files][delete_challengetasksubmission] - No Access for user %s",
                request.user.email
            )
            return HttpResponse("You do not have access to delete this file.", status=403)

        logger.debug(
            '[views_files][delete_challengetasksubmission] - %s is trying to delete submission %s',
            request.user.email,
            submission_uuid
        )

        user_is_submitter = submission.participant.user == request.user
        user_is_team_leader = team.team_leader == request.user.email
        user_is_manager = sciauthz.user_has_manage_permission(project.project_key)

        # Check that the user is either the team leader, the original submitter, or a manager
        if not user_is_submitter and not user_is_team_leader and not user_is_manager:
            logger.debug(
                "[views_files][delete_challengetasksubmission] - No Access for user %s",
                request.user.email
            )
            return HttpResponse("Only the original submitter, team leader, or challenge manager may delete this.", status=403)

        submission.deleted = True
        submission.save()

        # Do not give away the admin's email when notifying the team
        if user_is_manager:
            deleted_by = "an admin"
        else:
            deleted_by = request.user.email

        # Send an email notification to the team
        context = {
            'deleted_by': deleted_by,
            'project': project.project_key,
            'submission_uuid': submission_uuid
        }

        emails = [member.user.email for member in team.participant_set.all()]
        email_success = email_send(
            subject='DBMI Portal - Team Submission Deleted',
            recipients=emails,
            email_template='email_submission_deleted_notification',
            extra=context
        )

        return HttpResponse(status=200)

    return HttpResponse(status=500)
