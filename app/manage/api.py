from datetime import datetime
import json
import logging
import os
import shutil
import uuid
import zipfile

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string

from pyauth0jwt.auth0authenticate import user_auth_and_jwt

from contact.views import email_send
from hypatio.sciauthz_services import SciAuthZ
from hypatio.scireg_services import get_names
from manage.forms import EditHostedFileForm
from manage.utils import zip_submission_file
from projects.templatetags import projects_extras

from projects.models import AgreementForm
from projects.models import ChallengeTaskSubmission
from projects.models import DataProject
from projects.models import HostedFile
from projects.models import Participant
from projects.models import SignedAgreementForm
from projects.models import Team
from projects.models import TeamComment

# Get an instance of a logger
logger = logging.getLogger(__name__)

@user_auth_and_jwt
def set_dataproject_registration_status(request):
    """
    An HTTP POST endpoint for opening or closing registration to a DataProject.
    """

    user = request.user
    user_jwt = request.COOKIES.get("DBMI_JWT", None)

    project_key = request.POST.get("project_key")
    project = get_object_or_404(DataProject, project_key=project_key)

    sciauthz = SciAuthZ(settings.AUTHZ_BASE, user_jwt, user.email)
    is_manager = sciauthz.user_has_manage_permission(project_key)

    if not is_manager:
        logger.debug(
            '[HYPATIO][DEBUG][set_dataproject_registration_status] User {email} does not have MANAGE permissions for item {project_key}.'.format(
                email=user.email,
                project_key=project_key
            )
        )
        return HttpResponse("Error: permissions.", status=403)

    registration_status = request.POST.get("registration_status")

    if registration_status == "open":
        project.registration_open = True
    elif registration_status == "close":
        project.registration_open = False
    else:
        return HttpResponse("Error: invalid status.", status=400)

    project.save()

    response_html = render_to_string(
        'manage/registration-status.html',
        context={
            'project': project,
        }
    )

    return HttpResponse(response_html)

@user_auth_and_jwt
def set_dataproject_visible_status(request):
    """
    An HTTP POST endpoint for making a DataProject publicly visible or not.
    """

    user = request.user
    user_jwt = request.COOKIES.get("DBMI_JWT", None)

    project_key = request.POST.get("project_key")
    project = get_object_or_404(DataProject, project_key=project_key)

    sciauthz = SciAuthZ(settings.AUTHZ_BASE, user_jwt, user.email)
    is_manager = sciauthz.user_has_manage_permission(project_key)

    if not is_manager:
        logger.debug(
            '[HYPATIO][DEBUG][set_dataproject_visible_status] User {email} does not have MANAGE permissions for item {project_key}.'.format(
                email=user.email,
                project_key=project_key
            )
        )
        return HttpResponse("Error: permissions.", status=403)

    visibile_status = request.POST.get("visible_status")

    if visibile_status == "visible":
        project.visible = True
    elif visibile_status == "invisible":
        project.visible = False
    else:
        return HttpResponse("Error: Invalid status.", status=400)

    project.save()

    response_html = render_to_string(
        'manage/visible-status.html',
        context={
            'project': project,
        }
    )

    return HttpResponse(response_html)

@user_auth_and_jwt
def set_dataproject_details(request):
    """
    An HTTP POST endpoint for setting some details about a DataProject.
    """

    user = request.user
    user_jwt = request.COOKIES.get("DBMI_JWT", None)

    project_key = request.POST.get("project_key")
    project = get_object_or_404(DataProject, project_key=project_key)

    sciauthz = SciAuthZ(settings.AUTHZ_BASE, user_jwt, user.email)
    is_manager = sciauthz.user_has_manage_permission(project_key)

    if not is_manager:
        logger.debug(
            '[HYPATIO][DEBUG][set_dataproject_visible_status] User {email} does not have MANAGE permissions for item {project_key}.'.format(
                email=user.email,
                project_key=project_key
            )
        )
        return HttpResponse("Error: permissions.", status=403)

    name = request.POST.get("name", "")
    short_description = request.POST.get("short-description", "")
    description = request.POST.get("description", "")

    if name == "":
        return HttpResponse("Error: project name required.", status=400)
    if short_description == "":
        return HttpResponse("Error: project short description required.", status=400)
    if description == "":
        return HttpResponse("Error: project description required.", status=400)

    project.name = name
    project.short_description = short_description
    project.description = description

    try:
        project.save()
    except Exception as ex:
        return HttpResponse("Error: project details failed to save.", status=400)

    response_html = render_to_string(
        'manage/project-details.html',
        context={
            'project': project,
            'message': "Changes saved!"
        }
    )

    return HttpResponse(response_html)

@user_auth_and_jwt
def get_static_agreement_form_html(request):
    """
    An HTTP GET endpoint for Intercooler.js requests to get the HTML contents of an
    agreement form file and return them as HTML.
    """

    user = request.user
    user_jwt = request.COOKIES.get("DBMI_JWT", None)

    project_key = request.GET.get("project-key")
    project = get_object_or_404(DataProject, project_key=project_key)

    sciauthz = SciAuthZ(settings.AUTHZ_BASE, user_jwt, user.email)
    is_manager = sciauthz.user_has_manage_permission(project_key)

    if not is_manager:
        logger.debug(
            '[HYPATIO][DEBUG][get_static_agreement_form_html] User {email} does not have MANAGE permissions for item {project_key}.'.format(
                email=user.email,
                project_key=project_key
            )
        )
        return HttpResponse("Error: permissions.", status=403)

    agreement_form_id = request.GET.get('form-id', "")

    try:
        agreement_form = project.agreement_forms.get(id=agreement_form_id)
    except ObjectDoesNotExist:
        return HttpResponse("Error: form not found.", status=404)

    if agreement_form.form_file_path is None or agreement_form.form_file_path == "":
        return HttpResponse("Error: form file path is missing.", status=400)

    form_contents = projects_extras.get_html_form_file_contents(agreement_form.form_file_path)
    return HttpResponse(form_contents)

@user_auth_and_jwt
def get_hosted_file_edit_form(request):
    """
    An HTTP GET endpoint for requests to get an HTML form for editing an
    existing HostedFile.
    """

    user = request.user
    user_jwt = request.COOKIES.get("DBMI_JWT", None)

    project_key = request.GET.get("project-key")
    project = get_object_or_404(DataProject, project_key=project_key)

    sciauthz = SciAuthZ(settings.AUTHZ_BASE, user_jwt, user.email)
    is_manager = sciauthz.user_has_manage_permission(project_key)

    if not is_manager:
        logger.debug(
            '[HYPATIO][DEBUG][get_static_agreement_form_html] User {email} does not have MANAGE permissions for item {project_key}.'.format(
                email=user.email,
                project_key=project_key
            )
        )
        return HttpResponse("Error: permissions.", status=403)

    hosted_file_uuid = request.GET.get("hosted-file-uuid")

    try:
        hosted_file = HostedFile.objects.get(project=project, uuid=hosted_file_uuid)
    except ObjectDoesNotExist:
        return HttpResponse("Error: file not found.", status=404)

    edit_hosted_file_form = EditHostedFileForm(instance=hosted_file)

    response_html = render_to_string(
        'manage/edit-hosted-file-form.html',
        context={
            'form': edit_hosted_file_form,
            'file': hosted_file
        },
        request=request
    )
    return HttpResponse(response_html)

@user_auth_and_jwt
def process_hosted_file_edit_form_submission(request):
    """
    An HTTP POST endpoint for processing a submitted form for editing a hosted file.
    """

    user = request.user
    user_jwt = request.COOKIES.get("DBMI_JWT", None)

    file_uuid = request.POST.get("file-uuid")
    project_id = request.POST.get("project")
    project = get_object_or_404(DataProject, id=project_id)

    sciauthz = SciAuthZ(settings.AUTHZ_BASE, user_jwt, user.email)
    is_manager = sciauthz.user_has_manage_permission(project.project_key)

    if not is_manager:
        logger.debug(
            '[HYPATIO][DEBUG][get_static_agreement_form_html] User {email} does not have MANAGE permissions for item {project_key}.'.format(
                email=user.email,
                project_key=project.project_key
            )
        )
        return HttpResponse("Error: permissions.", status=403)

    hosted_file = HostedFile.objects.get(project=project, uuid=file_uuid)
    edit_hosted_file_form = EditHostedFileForm(request.POST, instance=hosted_file)

    # TODO show error messages
    if not edit_hosted_file_form.is_valid():
        return HttpResponse(edit_hosted_file_form.errors.as_json(), status=400)

    try:
        edit_hosted_file_form.save()
    except Exception:
        # TODO do something on failure
        return HttpResponse("Error: failed to save object", status=500)

    return HttpResponse("File updated.", status=200)

@user_auth_and_jwt
def download_signed_form(request):
    """
    An HTTP GET endpoint that returns a text file to the user containing the signed form's content.
    """

    form_id = request.GET.get("form_id")

    logger.debug('[HYPATIO][download_signed_form] ' + request.user.email + ' is trying to download signed form ' + form_id + '.')

    signed_form = get_object_or_404(SignedAgreementForm, id=form_id)

    user = request.user
    user_jwt = request.COOKIES.get("DBMI_JWT", None)
    project = signed_form.project

    sciauthz = SciAuthZ(settings.AUTHZ_BASE, user_jwt, user.email)
    is_manager = sciauthz.user_has_manage_permission(project.project_key)

    if not is_manager:
        logger.debug(
            '[HYPATIO][DEBUG][download_signed_form] User {email} does not have MANAGE permissions for item {project_key}.'.format(
                email=user.email,
                project_key=project.project_key
            )
        )
        return HttpResponse("Error: permissions.", status=403)

    affected_user = signed_form.user
    date_as_string = datetime.strftime(signed_form.date_signed, "%Y%m%d-%H%M")

    filename = affected_user.email + '-' + signed_form.agreement_form.short_name + '-' + date_as_string + '.txt'
    response = HttpResponse(signed_form.agreement_text, content_type='text/plain')
    response['Content-Disposition'] = 'attachment; filename={0}'.format(filename)
    return response

@user_auth_and_jwt
def change_signed_form_status(request):
    """
    An HTTP POST endpoint for changing a signed form's status and notifying the user.
    """

    status = request.POST.get("status")
    form_id = request.POST.get("form_id")
    administrator_message = request.POST.get("administrator_message")

    logger.debug('[HYPATIO][change_signed_form_status] ' + request.user.email + ' try to change status for signed form ' + form_id + ' to ' + status + '.')

    signed_form = get_object_or_404(SignedAgreementForm, id=form_id)
    affected_user = signed_form.user

    user = request.user
    user_jwt = request.COOKIES.get("DBMI_JWT", None)
    project = signed_form.project

    sciauthz = SciAuthZ(settings.AUTHZ_BASE, user_jwt, user.email)
    is_manager = sciauthz.user_has_manage_permission(project.project_key)

    if not is_manager:
        logger.debug(
            '[HYPATIO][DEBUG][change_signed_form_status] User {email} does not have MANAGE permissions for item {project_key}.'.format(
                email=user.email,
                project_key=project.project_key
            )
        )
        return HttpResponse("Error: permissions.", status=403)

    # First change the team's status
    if status == "approved":
        signed_form.status = 'A'
        signed_form.save()
    elif status == "rejected":
        signed_form.status = 'R'
        signed_form.save()

        logger.debug('[HYPATIO][change_signed_form_status] Emailing a rejection notification to the affected participant')

        # Send an email notification to the affected person
        context = {'signed_form': signed_form,
                   'administrator_message': administrator_message,
                   'site_url': settings.SITE_URL}

        email_success = email_send(subject='DBMI Portal - Signed Form Rejected',
                                   recipients=[affected_user.email],
                                   email_template='email_signed_form_rejection_notification',
                                   extra=context)

        # If the user is a participant on a team, then the team status may need to be changed
        try:
            participant = Participant.objects.get(user=affected_user, project=signed_form.project)
            team = participant.team
        except ObjectDoesNotExist:
            participant = None
            team = None

        # If the team is in an Active status, move the team status down to Ready and remove everyone's VIEW permissions
        if team is not None and team.status == "Active":
            team.status = "Ready"
            team.save()

            for member in team.participant_set.all():
                sciauthz = SciAuthZ(settings.AUTHZ_BASE, request.COOKIES.get("DBMI_JWT", None), request.user.email)
                sciauthz.remove_view_permission(signed_form.project.project_key, member.user.email)

            logger.debug('[HYPATIO][change_signed_form_status] Emailing the whole team that their status has been moved to Ready because someone has a pending form')

            # Send an email notification to the team
            context = {'status': "ready",
                       'reason': 'Your team has been temporarily disabled because of an issue with a team members\' forms. Challenge administrators will resolve this shortly.',
                       'project': signed_form.project,
                       'site_url': settings.SITE_URL}

            # Email list
            emails = [member.user.email for member in team.participant_set.all()]

            email_success = email_send(subject='DBMI Portal - Team Status Changed',
                                       recipients=emails,
                                       email_template='email_new_team_status_notification',
                                       extra=context)
    else:
        logger.debug('[HYPATIO][change_signed_form_status] Given status "' + status + '" not one of allowed statuses.')
        return HttpResponse(500)

    return HttpResponse(200)

@user_auth_and_jwt
def save_team_comment(request):
    """
    An HTTP POST endpoint for saving a comment made about a team by a challenge administrator.
    """

    project_key = request.POST.get("project")
    team_leader = request.POST.get("team")
    comment = request.POST.get("comment")

    logger.debug('[HYPATIO][save_team_comment] ' + request.user.email + ' entered a comment about team ' + team_leader + '.')

    project = DataProject.objects.get(project_key=project_key)

    user = request.user
    user_jwt = request.COOKIES.get("DBMI_JWT", None)

    sciauthz = SciAuthZ(settings.AUTHZ_BASE, user_jwt, user.email)
    is_manager = sciauthz.user_has_manage_permission(project.project_key)

    if not is_manager:
        logger.debug(
            '[HYPATIO][DEBUG][save_team_comment] User {email} does not have MANAGE permissions for item {project_key}.'.format(
                email=user.email,
                project_key=project.project_key
            )
        )
        return HttpResponse("Error: permissions.", status=403)

    team = Team.objects.get(team_leader__email=team_leader, data_project=project)

    new_comment = TeamComment(user=request.user,
                              team=team,
                              text=comment)
    new_comment.save()

    return HttpResponse(200)

@user_auth_and_jwt
def set_team_status(request):
    """
    An HTTP POST endpoint to set a team's status, assign the correct permissions, and notify team members.
    """

    project_key = request.POST.get("project")
    team_leader = request.POST.get("team")
    status = request.POST.get("status")

    logger.debug('[HYPATIO][set_team_status] ' + request.user.email + ' changing team ' + team_leader + ' for project ' + project_key + ' to status of ' + status + '.')

    project = DataProject.objects.get(project_key=project_key)

    user = request.user
    user_jwt = request.COOKIES.get("DBMI_JWT", None)

    sciauthz = SciAuthZ(settings.AUTHZ_BASE, user_jwt, user.email)
    is_manager = sciauthz.user_has_manage_permission(project.project_key)

    if not is_manager:
        logger.debug(
            '[HYPATIO][DEBUG][set_team_status] User {email} does not have MANAGE permissions for item {project_key}.'.format(
                email=user.email,
                project_key=project.project_key
            )
        )
        return HttpResponse("Error: permissions.", status=403)

    team = Team.objects.get(team_leader__email=team_leader, data_project=project)

    # First change the team's status
    if status == "pending":
        team.status = "Pending"
        team.save()
    elif status == "ready":
        team.status = "Ready"
        team.save()
    elif status == "active":
        team.status = "Active"
        team.save()
    elif status == "deactivated":
        team.status = "Deactivated"
        team.save()
    else:
        logger.debug('[HYPATIO][set_team_status] Given status "' + status + '" not one of allowed statuses.')
        return HttpResponse(500)

    logger.debug('[HYPATIO][set_team_status] Adjusting VIEW permissions for team members.')

    # If a status is anything other than active, remove VIEW permissions
    if status in ["active"]:
        for member in team.participant_set.all():
            sciauthz = SciAuthZ(settings.AUTHZ_BASE, request.COOKIES.get("DBMI_JWT", None), request.user.email)
            sciauthz.create_view_permission(project_key, member.user.email)
    else:
        for member in team.participant_set.all():
            sciauthz = SciAuthZ(settings.AUTHZ_BASE, request.COOKIES.get("DBMI_JWT", None), request.user.email)
            sciauthz.remove_view_permission(project_key, member.user.email)

    logger.debug('[HYPATIO][set_team_status] Emailing a notification to team members.')

    # Send an email notification to the team
    context = {'status': status,
               'project': project,
               'site_url': settings.SITE_URL}

    # Email list
    emails = [member.user.email for member in team.participant_set.all()]

    email_success = email_send(subject='DBMI Portal - Team Status Changed',
                               recipients=emails,
                               email_template='email_new_team_status_notification',
                               extra=context)

    return HttpResponse(200)

@user_auth_and_jwt
def delete_team(request):
    """
    Delete a team and notify members.
    """

    project_key = request.POST.get("project")
    team_leader = request.POST.get("team")
    administrator_message = request.POST.get("administrator_message")

    logger.debug('[HYPATIO][delete_team] ' + request.user.email + ' is deleting team ' + team_leader + ' for project ' + project_key + '.')

    project = DataProject.objects.get(project_key=project_key)

    user = request.user
    user_jwt = request.COOKIES.get("DBMI_JWT", None)

    sciauthz = SciAuthZ(settings.AUTHZ_BASE, user_jwt, user.email)
    is_manager = sciauthz.user_has_manage_permission(project.project_key)

    if not is_manager:
        logger.debug(
            '[HYPATIO][DEBUG][delete_team] User {email} does not have MANAGE permissions for item {project_key}.'.format(
                email=user.email,
                project_key=project.project_key
            )
        )
        return HttpResponse("Error: permissions.", status=403)

    team = Team.objects.get(team_leader__email=team_leader, data_project=project)

    logger.debug('[HYPATIO][delete_team] Removing all VIEW permissions for team members.')

    # First revoke all VIEW permissions
    for member in team.participant_set.all():
        sciauthz = SciAuthZ(settings.AUTHZ_BASE, request.COOKIES.get("DBMI_JWT", None), request.user.email)
        sciauthz.remove_view_permission(project_key, member.user.email)

    logger.debug('[HYPATIO][delete_team] Sending a notification to team members.')

    # Then send a notification to the team members
    context = {'administrator_message': administrator_message,
               'project': project,
               'site_url': settings.SITE_URL}

    emails = [member.user.email for member in team.participant_set.all()]

    email_success = email_send(subject='DBMI Portal - Team Deleted',
                               recipients=emails,
                               email_template='email_team_deleted_notification',
                               extra=context)

    logger.debug('[HYPATIO][delete_team] Deleting the team from the database.')

    # Then delete the team
    team.delete()

    logger.debug('[HYPATIO][delete_team] Team ' + team_leader + ' for project ' + project_key + ' successfully deleted.')

    return HttpResponse(200)

@user_auth_and_jwt
def download_team_submissions(request, project_key, team_leader_email):
    """
    An HTTP GET endpoint that handles downloads of participant submission files. Checks
    that the requesting user has proper permissions to access this file. Downloads all
    of the team's submissions into one zip file, with each submission in it's own zip
    file containing a json file with metadata about the upload.
    """
    logger.debug('download_team_submissions: {}'.format(request.method))

    if request.method == "GET":

        # Check permissions in SciAuthZ.
        user_jwt = request.COOKIES.get("DBMI_JWT", None)
        sciauthz = SciAuthZ(settings.AUTHZ_BASE, user_jwt, request.user.email)
        is_manager = sciauthz.user_has_manage_permission(project_key)

        if not is_manager:
            logger.debug("[download_team_submissions] - No Access for user " + request.user.email)
            return HttpResponse("You do not have access to download this file.", status=403)

        project = get_object_or_404(DataProject, project_key=project_key)
        team = get_object_or_404(Team, data_project=project, team_leader__email=team_leader_email)

        # A list of file paths to each submission's zip file.
        zipped_submissions_paths = []

        # Get all submissions made by this team for this project.
        submissions = ChallengeTaskSubmission.objects.filter(
            challenge_task__in=project.challengetask_set.all(),
            participant__in=team.participant_set.all(),
            deleted=False
        )

        # For each submission, create a zip file and add the path to the list of zip files.
        for submission in submissions:
            zip_file_path = zip_submission_file(submission, request)
            zipped_submissions_paths.append(zip_file_path)

        # Create a directory to store the final encompassing zip file.
        final_zip_file_directory = "/tmp/" + str(uuid.uuid4())
        if not os.path.exists(final_zip_file_directory):
            os.makedirs(final_zip_file_directory)

        # Combine all the zipped tasks into one file zip file.
        final_zip_file_name = project_key + "__team-submissions__" + team_leader_email + ".zip"
        final_zip_file_path = os.path.join(final_zip_file_directory, final_zip_file_name)
        with zipfile.ZipFile(final_zip_file_path, mode="w") as zf:
            for zip_file in zipped_submissions_paths:
                zf.write(zip_file, arcname=os.path.basename(zip_file))

        # Prepare the zip file to be served.
        final_zip_file = open(final_zip_file_path, 'rb')
        response = HttpResponse(final_zip_file, content_type='application/force-download')
        response['Content-Disposition'] = 'attachment; filename="%s"' % final_zip_file_name

        # Delete all the directories holding the zip files.
        for path in zipped_submissions_paths:
            shutil.rmtree(os.path.dirname(os.path.realpath((path))))

        # Delete the final zip file.
        shutil.rmtree(final_zip_file_directory)

        return response

@user_auth_and_jwt
def download_submission(request, fileservice_uuid):
    """
    An HTTP GET endpoint that allows a user to download a ChallengeTaskSubmission's
    file from AWS/fileservice.
    """

    if request.method == "GET":

        submission = get_object_or_404(ChallengeTaskSubmission, uuid=fileservice_uuid)
        project = submission.challenge_task.data_project

        # Check permissions in SciAuthZ.
        user_jwt = request.COOKIES.get("DBMI_JWT", None)
        sciauthz = SciAuthZ(settings.AUTHZ_BASE, user_jwt, request.user.email)
        is_manager = sciauthz.user_has_manage_permission(project.project_key)

        if not is_manager:
            logger.debug("[download_submission] - No Access for user " + request.user.email)
            return HttpResponse("You do not have access to download this file.", status=403)

        # Download the submission file from fileservice and zip it up with the info json.
        zip_file_path = zip_submission_file(submission, request)
        zip_file_name = os.path.basename(zip_file_path)

        # Prepare the zip file to be served.
        final_zip_file = open(zip_file_path, 'rb')
        response = HttpResponse(final_zip_file, content_type='application/force-download')
        response['Content-Disposition'] = 'attachment; filename="%s"' % zip_file_name

        # Delete the directory containing the zip file.
        shutil.rmtree(os.path.dirname(os.path.realpath((zip_file_path))))

        return response

@user_auth_and_jwt
def download_email_list(request):
    """
    Downloads a text file containing the email addresses of participants of a given project
    with filters accepted as GET parameters. Accepted filters include: team, team status,
    agreement form ID, and agreement form status.
    """

    logger.debug("[views_manage][download_email_list] - Attempting file download.")

    project_key = request.GET.get("project")
    project = get_object_or_404(DataProject, project_key=project_key)

    # Check Permissions in SciAuthZ
    user_jwt = request.COOKIES.get("DBMI_JWT", None)
    sciauthz = SciAuthZ(settings.AUTHZ_BASE, user_jwt, request.user.email)
    is_manager = sciauthz.user_has_manage_permission(project_key)

    if not is_manager:
        logger.debug("[views_manage][download_email_list] - No Access for user " + request.user.email)
        return HttpResponse("You do not have access to download this file.", status=403)

    # Filters used to determine the list of participants
    filter_team = request.GET.get("team-id", None)
    filter_team_status = request.GET.get("team-status", None)
    filter_signed_agreement_form = request.GET.get("agreement-form-id", None)
    filter_signed_agreement_form_status = request.GET.get("agreement-form-status", None)

    # Apply filters that narrow the scope of teams
    teams = Team.objects.filter(data_project=project)

    if filter_team:
        teams = teams.filter(id=filter_team)
    if filter_team_status:
        teams = teams.filter(status=filter_team_status)

    # Apply filters that narrow the list of participants
    participants = Participant.objects.filter(team__in=teams)

    if filter_signed_agreement_form:
        agreement_form = AgreementForm.objects.get(id=filter_signed_agreement_form)

        # Find all signed instances of this form
        signed_forms = SignedAgreementForm.objects.filter(agreement_form=agreement_form)
        if filter_signed_agreement_form_status:
            signed_forms = signed_forms.filter(status=filter_signed_agreement_form_status)

        # Narrow down the participant list with just those who have these signed forms
        signed_forms_users = signed_forms.values_list('user', flat=True)
        participants = participants.filter(user__in=signed_forms_users)

    # Query SciReg to get a dictionary of first and last names for each participant
    names = json.loads(get_names(user_jwt, participants, project_key))

    # Build a string that will be the contents of the file
    file_contents = ""
    for participant in participants:

        first_name = ""
        last_name = ""

        # Look in our dictionary of names from SciReg for this participant
        try:
            name = names[participant.user.email]
            first_name = name['first_name']
            last_name = name['last_name']
        except (KeyError, IndexError):
            pass

        file_contents += participant.user.email + " " + first_name + " " + last_name +  "\n"

    response = HttpResponse(file_contents, content_type='text/plain')
    response['Content-Disposition'] = 'attachment; filename="%s"' % 'pending_participants.txt'

    return response
