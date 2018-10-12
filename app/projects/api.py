from copy import copy
from datetime import datetime
import json
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import User
from django.core import exceptions
from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse
from django.http import HttpResponse
from django.http import QueryDict
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect

from contact.views import email_send
from hypatio import file_services as fileservice
from hypatio.file_services import get_download_url
from hypatio.sciauthz_services import SciAuthZ
from projects.templatetags import projects_extras

from projects.models import ChallengeTask
from projects.models import ChallengeTaskSubmission
from projects.models import DataProject
from projects.models import HostedFile
from projects.models import HostedFileDownload
from projects.models import Participant
from projects.models import Team

from pyauth0jwt.auth0authenticate import user_auth_and_jwt

logger = logging.getLogger(__name__)

@user_auth_and_jwt
def finalize_team(request):
    """
    An HTTP POST endpoint for team leaders to mark their team as ready and send an email notification to contest managers.
    """

    project_key = request.POST.get("project_key")
    team = request.POST.get("team")

    project = DataProject.objects.get(project_key=project_key)
    team = Team.objects.get(team_leader__email=team, data_project=project)

    if request.user.email != team.team_leader.email:
        logger.debug(
            "User {email} is not a team leader.".format(
                email=request.user.email
            )
        )
        return HttpResponse("Error: permissions.", status=403)

    team.status = 'Ready'
    team.save()

    # TODO Eventually this should be replaced by checking the dataproject's leader
    contest_managers = ['ouzuner@gmu.edu', 'filannim@csail.mit.edu', 'stubbs@simmons.edu']

    context = {'team_leader': team,
               'project': project_key,
               'site_url': settings.SITE_URL}

    email_success = email_send(subject='DBMI Portal - Finalized Team',
                               recipients=contest_managers,
                               email_template='email_finalized_team_notification',
                               extra=context)

    return HttpResponse(200)

@user_auth_and_jwt
def approve_team_join(request):
    """
    An HTTP POST endpoint for team leaders to approve requests from others to join their team.
    """

    project_key = request.POST.get("project_key")
    participant_email = request.POST.get("participant")

    project = DataProject.objects.get(project_key=project_key)

    try:
        team = Team.objects.get(
            team_leader=request.user,
            data_project=project
        )
    except ObjectDoesNotExist:
        team = None

    if request.user.email != team.team_leader.email:
        logger.debug(
            "User {email} is not a team leader.".format(
                email=request.user.email
            )
        )
        return HttpResponse("Error: permissions.", status=403)

    try:
        participant_user = User.objects.get(email=participant_email)
        participant = Participant.objects.get(
            user=participant_user,
            data_challenge=project
        )
    except ObjectDoesNotExist:
        participant = None

    participant.assign_approved(team)
    participant.save()

    return HttpResponse(200)

@user_auth_and_jwt
def reject_team_join(request):
    """
    An HTTP POST endpoint for team leaders to reject requests from others to join their team.
    """

    project_key = request.POST.get("project_key")
    participant_email = request.POST.get("participant")

    project = DataProject.objects.get(project_key=project_key)

    try:
        participant_user = User.objects.get(email=participant_email)
        participant = Participant.objects.get(
            user=participant_user,
            data_challenge=project
        )
    except ObjectDoesNotExist:
        logger.debug('Participant not found.')
        return HttpResponse('Error.', status=404)

    if request.user.email != participant.team.team_leader.email:
        logger.debug(
            "User {email} is not a team leader.".format(
                email=request.user.email
            )
        )
        return HttpResponse("Error: permissions.", status=403)

    participant.delete()

    return HttpResponse(200)

@user_auth_and_jwt
def leave_team(request):
    """
    An HTTP POST endpoint for removing the participant from whatever team they are currently on or have requested to be on.
    """

    project_key = request.POST.get("project_key", "")

    logger.debug("[HYPATIO][leave_team] User " + request.user.email + " trying to leave their current team for project " + project_key + ".")

    try:
        project = DataProject.objects.get(project_key=project_key)
    except ObjectDoesNotExist:
        logger.error("[HYPATIO][leave_team] DataProject not found for given project_key: " + project_key)
        return HttpResponse(500)

    # TODO user does not have permissions to remove their view permission (whether or not it exists)
    # Remove VIEW permissions on the DataProject
    # sciauthz = SciAuthZ(settings.AUTHZ_BASE, request.COOKIES.get("DBMI_JWT", None), request.user.email)
    # sciauthz.remove_view_permission(project_key, request.user.email)

    # TODO remove team leader's scireg permissions
    # ...

    participant = Participant.objects.get(user=request.user, data_challenge=project)
    participant.team = None
    participant.pending = False
    participant.approved = False
    participant.team_wait_on_leader_email = None
    participant.team_wait_on_leader = False
    participant.save()

    return redirect('/projects/' + request.POST.get('project_key') + '/')

@user_auth_and_jwt
def join_team(request):
    """
    An HTTP POST endpoint for a user to try to join a team by entering the team leader's email.
    """

    project_key = request.POST.get("project_key")
    project = DataProject.objects.get(project_key=project_key)

    team_leader = request.POST.get("team_leader")

    try:
        participant = Participant.objects.get(user=request.user, data_challenge=project)
    except ObjectDoesNotExist:
        participant = Participant(user=request.user, data_challenge=project)
        participant.save()

    try:
        # If this team leader has already created a team, add the person to the team in a pending status
        team = Team.objects.get(team_leader__email__iexact=team_leader, data_project=project)

        # Only allow a new participant to join a team that is still in a pending or ready state
        if team.status in ['Pending', 'Ready']:
            participant.team = team
            participant.team_pending = True
            participant.save()
        # Otherwise, let them know why they can't join the team
        else:
            msg = "The team you are trying to join has already been finalized and is not accepting new members. " + \
                  "If you would like to join this team, please have the team leader contact the challenge " + \
                  "administrators for help."
            messages.error(request, msg)

            return redirect('/projects/' + request.POST.get('project_key') + '/')
    except ObjectDoesNotExist:
        # If this team leader has not yet created a team, mark the person as waiting
        participant.team_wait_on_leader_email = team_leader
        participant.team_wait_on_leader = True
        participant.save()
        team = None

    # Send email to team leader informing them of a pending member
    if team is not None:
        context = {'member_email': request.user.email,
                   'project': project,
                   'site_url': settings.SITE_URL}

        email_success = email_send(subject='DBMI Portal - Pending Member',
                                   recipients=[team_leader],
                                   email_template='email_pending_member_notification',
                                   extra=context)

    logger.debug('[HYPATIO][join_team] - Creating Profile Permissions')

    # Create record to allow leader access to profile.
    sciauthz = SciAuthZ(settings.AUTHZ_BASE, request.COOKIES.get("DBMI_JWT", None), request.user.email)
    sciauthz.create_profile_permission(team_leader, project_key)

    return redirect('/projects/' + request.POST.get('project_key') + '/')

@user_auth_and_jwt
def create_team(request):
    """
    An HTTP POST endpoint for users to create a new team and be its team leader.
    """

    project_key = request.POST.get("project_key")
    project = DataProject.objects.get(project_key=project_key)
    new_team = Team.objects.create(team_leader=request.user, data_project=project)

    try:
        participant = Participant.objects.get(user=request.user, data_challenge=project)
    except ObjectDoesNotExist:
        participant = Participant(user=request.user, data_challenge=project)
        participant.save()

    participant.assign_approved(new_team)
    participant.save()

    # Find anyone whose waiting on this team leader and link them to the new team.
    waiting_participants = Participant.objects.filter(
        team_wait_on_leader_email=request.user.email,
        data_challenge=project
    )

    for participant in waiting_participants:
        participant.assign_pending(new_team)
        participant.save()

    return redirect('/projects/' + project_key + '/')

@user_auth_and_jwt
def download_dataset(request):
    """
    An HTTP GET endpoint that handles downloads for project level files. Checks that the requesting user
    has view permissions on the given project before allowing a download.
    """

    logger.debug("[download_dataset] - Attempting file download.")

    file_uuid = request.GET.get("file_uuid")
    file_to_download = get_object_or_404(HostedFile, uuid=file_uuid)
    project_key = file_to_download.project.project_key

    # Check if this file is enabled for download.
    if not projects_extras.is_hostedfile_currently_enabled(file_to_download):
        logger.debug("[download_dataset] - File not allowed for download attempted by " + request.user.email)
        return HttpResponse("You do not have access to download this file.", status=403)

    # Check for necessary permissions in SciAuthZ.
    user_jwt = request.COOKIES.get("DBMI_JWT", None)
    sciauthz = SciAuthZ(settings.AUTHZ_BASE, user_jwt, request.user.email)

    if not sciauthz.user_has_single_permission(project_key, "VIEW"):
        logger.debug("[download_dataset] - No Access for user " + request.user.email)
        return HttpResponse("You do not have access to download this file.", status=403)

    # Save a record of this person downloading this file.
    HostedFileDownload.objects.create(user=request.user, hosted_file=file_to_download)

    s3_filename = file_to_download.file_location + "/" + file_to_download.file_name
    logger.debug("[download_dataset] - User " + request.user.email + " is downloading file " + s3_filename + " from bucket " + settings.S3_BUCKET + ".")

    download_url = get_download_url(s3_filename)

    response = redirect(download_url)
    response['Content-Disposition'] = 'attachment'
    response['filename'] = file_to_download.file_name

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
            logger.debug("[upload_challengetasksubmission_file] - No Access for user " + request.user.email)
            return HttpResponse("You do not have access to upload this file.", status=403)

        if filename.split(".")[-1] != "zip":
            logger.error('Not a zip file.')
            return HttpResponse("Only .zip files are accepted", status=400)

        try:
            task = ChallengeTask.objects.get(id=task_id)
        except exceptions.ObjectDoesNotExist:
            logger.error('Task not found with id {id}'.format(id=task_id))
            return HttpResponse('Task not found', status=400)

        # Only allow a submission if the task is still open.
        if not projects_extras.is_challengetask_currently_enabled(task):
            logger.error("[upload_challengetasksubmission_file] - User " + request.user.email + " is trying to submit task " + task.title + " after close time.")
            return HttpResponse("This task is no longer open for submissions", status=400)

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
            submission_info['submitted_on'] = datetime.strftime(datetime.now(), "%Y%m%d_%H%M") + " (UTC)"

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
    An HTTP POST endpoint that marks a ChallengeTaskSubmission as deleted so
    it will not be counted against their total submission count for a contest.
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
                "[delete_challengetasksubmission] - No Access for user %s",
                request.user.email
            )
            return HttpResponse("You do not have access to delete this file.", status=403)

        logger.debug(
            '[delete_challengetasksubmission] - %s is trying to delete submission %s',
            request.user.email,
            submission_uuid
        )

        user_is_submitter = submission.participant.user == request.user
        user_is_team_leader = team.team_leader == request.user.email
        user_is_manager = sciauthz.user_has_manage_permission(project.project_key)

        # Check that the user is either the team leader, the original submitter, or a manager
        if not user_is_submitter and not user_is_team_leader and not user_is_manager:
            logger.debug(
                "[delete_challengetasksubmission] - No Access for user %s",
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
