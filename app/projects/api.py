from copy import copy
from datetime import datetime
import json
import importlib
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import User
from django.core import exceptions
from django.core.exceptions import ObjectDoesNotExist
from django.template.exceptions import TemplateDoesNotExist
from django.http import JsonResponse
from django.http import HttpResponse
from django.http import QueryDict
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.template import loader
from django.core.files.base import ContentFile
from dal import autocomplete

from hypatio.auth0authenticate import user_auth_and_jwt
from contact.views import email_send
from hypatio import file_services as fileservice
from hypatio.file_services import get_download_url
from hypatio.sciauthz_services import SciAuthZ
from hypatio.dbmiauthz_services import DBMIAuthz
from projects.templatetags import projects_extras
from projects.utils import notify_supervisors_of_task_submission
from projects.utils import notify_task_submitters
from pdf.renderers import render_pdf
from projects.panels import DataProjectSignupPanel
from projects.panels import SIGNUP_STEP_CURRENT_STATUS

from projects.models import AgreementForm
from projects.models import ChallengeTask
from projects.models import ChallengeTaskSubmission
from projects.models import DataProject
from projects.models import HostedFile
from projects.models import HostedFileDownload
from projects.models import Participant
from projects.models import SignedAgreementForm
from projects.models import Team
from projects.models import SIGNED_FORM_REJECTED
from projects.models import HostedFileSet
from projects.models import InstitutionalOfficial

logger = logging.getLogger(__name__)


class HostedFileSetAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        # Don't forget to filter out results depending on the visitor !
        if not self.request.user.is_authenticated:
            return HostedFileSet.objects.none()

        queryset = HostedFileSet.objects.all()

        project = self.forwarded.get('project', None)
        if project:
            logger.debug(f'HostedFileSetAutocomplete: Filtering on "{project}"')
            queryset = queryset.filter(project=project)

        if self.q:
            logger.debug(f'HostedFileSetAutocomplete: Filtering on "{self.q}"')
            queryset = queryset.filter(title__istartswith=self.q)

        return queryset

    def create_object(self, text):
        """Create an object given a text."""
        project = get_object_or_404(DataProject, id=self.forwarded.get('project'))
        return self.get_queryset().get_or_create(title=text, project=project)[0]


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

    # Convert the comma separated string of emails into a list.
    supervisor_emails = project.project_supervisors.split(",")

    context = {'team_leader': team,
               'project': project_key,
               'site_url': settings.SITE_URL}

    email_success = email_send(
        subject='DBMI Portal - Finalized Team',
        recipients=supervisor_emails,
        email_template='email_finalized_team_notification',
        extra=context
    )

    return HttpResponse(200)

@user_auth_and_jwt
def approve_team_join(request):
    """
    An HTTP POST endpoint for team leaders to approve requests from others to join their team.
    """

    project_key = request.POST.get("project_key")
    participant_email = request.POST.get("participant")

    project = DataProject.objects.get(project_key=project_key)

    logger.debug(
        '[HYPATIO][DEBUG][approve_team_join] User {user} is attempting to approve {participant} to join their team for project {project_key}.'.format(
            user=request.user.email,
            participant=participant_email,
            project_key=project_key
        )
    )

    try:
        team = Team.objects.get(
            team_leader=request.user,
            data_project=project
        )
    except ObjectDoesNotExist:
        team = None

    if request.user.email != team.team_leader.email:
        logger.error(
            "[HYPATIO][DEBUG][approve_team_join] User {email} is not the team leader and thus cannot add people.".format(
                email=request.user.email
            )
        )
        return HttpResponse("Error: permissions.", status=403)

    try:
        participant_user = User.objects.get(email=participant_email)
        participant = Participant.objects.get(
            user=participant_user,
            project=project
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

    logger.debug(
        '[HYPATIO][DEBUG][reject_team_join] User {user} is attempting to reject {participant} from joining their team for project {project_key}.'.format(
            user=request.user.email,
            participant=participant_email,
            project_key=project_key
        )
    )

    try:
        participant_user = User.objects.get(email=participant_email)
        participant = Participant.objects.get(
            user=participant_user,
            project=project
        )
    except ObjectDoesNotExist:
        logger.debug('Participant not found.')
        return HttpResponse('Error.', status=404)

    if request.user.email != participant.team.team_leader.email:
        logger.error(
            "[HYPATIO][DEBUG][reject_team_join] User {email} is not the team leader and thus cannot reject people.".format(
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
    # sciauthz = SciAuthZ(request.COOKIES.get("DBMI_JWT", None), request.user.email)
    # sciauthz.remove_view_permission(project_key, request.user.email)

    # TODO remove team leader's scireg permissions
    # ...

    participant = Participant.objects.get(user=request.user, project=project)
    participant.team = None
    participant.team_pending = False
    participant.team_approved = False
    participant.team_wait_on_leader_email = None
    participant.team_wait_on_leader = False
    participant.save()

    return redirect('/projects/' + request.POST.get('project_key') + '/')

@user_auth_and_jwt
def join_team(request):
    """
    An HTTP POST endpoint for a user to try to join a team by entering the team leader's email.
    """

    project_key = request.POST.get("project_key", None)

    try:
        project = DataProject.objects.get(project_key=project_key)
    except ObjectDoesNotExist:
        logger.error("[HYPATIO][join_team] User {email} hit the join_team api method without a project key provided.".format(
            email=request.user.email
        ))
        return redirect('/')

    team_leader = request.POST.get("team_leader", None)

    logger.debug("[HYPATIO][join_team] User {email} is requesting to join team {team} for project {project}.".format(
        email=request.user.email,
        team=team_leader,
        project=project_key
    ))

    try:
        participant = Participant.objects.get(user=request.user, project=project)
    except ObjectDoesNotExist:
        participant = Participant(user=request.user, project=project)
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

    # Create record to allow leader access to profile.
    sciauthz = SciAuthZ(request.COOKIES.get("DBMI_JWT", None), request.user.email)
    sciauthz.create_profile_permission(team_leader, project_key)

    return redirect('/projects/' + request.POST.get('project_key') + '/')

@user_auth_and_jwt
def create_team(request):
    """
    An HTTP POST endpoint for users to create a new team and be its team leader.
    """

    project_key = request.POST.get("project_key")
    project = DataProject.objects.get(project_key=project_key)

    logger.debug("[HYPATIO][create_team] User " + request.user.email + " is trying to create a team for project " + project_key + ".")

    new_team, created = Team.objects.get_or_create(team_leader=request.user, data_project=project)

    try:
        participant = Participant.objects.get(user=request.user, project=project)
    except ObjectDoesNotExist:
        participant = Participant(user=request.user, project=project)
        participant.save()

    participant.assign_approved(new_team)
    participant.save()

    # Find anyone whose waiting on this team leader and link them to the new team.
    waiting_participants = Participant.objects.filter(
        team_wait_on_leader_email=request.user.email,
        project=project
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

    if not DBMIAuthz.user_has_view_permission(request=request, project_key=project_key):
        logger.debug("[download_dataset] - No Access for user " + request.user.email)
        return HttpResponse("You do not have access to download this file.", status=403)

    # Save a record of this person downloading this file.
    HostedFileDownload.objects.create(user=request.user, hosted_file=file_to_download)

    file_uri = f"{file_to_download.project.bucket.uri}/{file_to_download.file_location}/{file_to_download.file_name}"
    logger.debug(f"[download_dataset] - User {request.user.email} is downloading file {file_uri}.")

    download_url = get_download_url(file_uri)

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

    if request.method == 'POST':
        logger.debug('post')

        # Assembles the form and runs validation.
        filename = request.POST.get('filename')
        project_key = request.POST.get('project_key')
        task_id = request.POST.get('task_id')

        if not filename or not project_key or not task_id:
            logger.error('No filename, project, or task!')
            return HttpResponse('Filename, project, task are required', status=400)

        project = get_object_or_404(DataProject, project_key=project_key)

        # If the project requires authorization to access, check for permissions before allowing submission
        if project.requires_authorization:

            # Get their permission for this project
            has_permission = False
            try:
                participant = Participant.objects.get(user=request.user, project=project)
                has_permission = participant.permission == "VIEW"
                if not has_permission:
                    logger.debug(f"[{project_key}][{request.user.email}] No  VIEW access for user")
            except ObjectDoesNotExist as e:
                logger.exception(f"Participant does not exist", exc_info=False, extra={
                    "request": request, "project": project_key, "user": request.user,
                })

            # Check AuthZ
            if not has_permission:
                logger.warning(
                    f"[{project_key}][{request.user.email}] Local permission "
                    f"does not exist, checking DBMI AuthZ for "
                )

                # Check that user has permissions to be submitting files for this project.
                user_jwt = request.COOKIES.get("DBMI_JWT", None)
                sciauthz = SciAuthZ(user_jwt, request.user.email)

                if not sciauthz.user_has_single_permission(project_key, "VIEW", request.user.email):
                    logger.warning(f"[{project_key}][{request.user.email}] No Access")
                    return HttpResponse("You do not have access to upload this file.", status=403)

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
            participant = get_object_or_404(Participant, user=request.user, project=project)
            task = get_object_or_404(ChallengeTask, id=submission_info['task_id'])

            # Get the team, although it could be None for projects with no teams.
            team = participant.team

            # Remove a few unnecessary fields.
            del submission_info['csrfmiddlewaretoken']
            del submission_info['location']

            # Add some more fields
            submission_info['submitted_by'] = request.user.email

            if participant.team is not None:
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
                submission_info=submission_info_json,
                file_type=task.submission_file_type,
            )

            # Send an email notification to the submitters.
            notify_task_submitters(project, participant, task, submission_info_json)

            # If the task is configured to send notifications to supervisors, do so.
            if task.notify_supervisors_of_submissions:
                notify_supervisors_of_task_submission(project, participant, task, submission_info_json)

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
        sciauthz = SciAuthZ(user_jwt, request.user.email)

        submission_uuid = request.POST.get('submission_uuid')
        submission = ChallengeTaskSubmission.objects.get(uuid=submission_uuid)

        project = submission.participant.project

        logger.debug(
            '[delete_challengetasksubmission] - %s is trying to delete submission %s',
            request.user.email,
            submission_uuid
        )

        user_is_submitter = submission.participant.user == request.user
        user_is_manager = sciauthz.user_has_manage_permission(project.project_key)

        if project.has_teams:
            team = submission.participant.team
            user_is_team_leader = team.team_leader == request.user.email

            # Check that the user is either the team leader, the original submitter, or a manager.
            if not user_is_submitter and not user_is_team_leader and not user_is_manager:
                logger.debug(
                    "[delete_challengetasksubmission] - No Access for user %s",
                    request.user.email
                )
                return HttpResponse("Only the original submitter, team leader, or challenge manager may delete this.", status=403)

            # Prepare the email notification to send.
            emails = [member.user.email for member in team.participant_set.all()]
            subject = 'DBMI Portal - Team Submission Deleted'

        else:
            # Check that the user is either the the original submitter or a manager.
            if not user_is_submitter and not user_is_manager:
                logger.debug(
                    "[delete_challengetasksubmission] - No Access for user %s",
                    request.user.email
                )
                return HttpResponse("Only the original submitter, team leader, or challenge manager may delete this.", status=403)

            # Prepare the email notification to send.
            emails = [submission.participant.user.email]
            subject = 'DBMI Portal - Submission Deleted'

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

        email_success = email_send(
            subject=subject,
            recipients=emails,
            email_template='email_submission_deleted_notification',
            extra=context
        )

        return HttpResponse(status=200)

    return HttpResponse(status=500)

@user_auth_and_jwt
def save_signed_agreement_form(request):
    """
    An HTTP POST endpoint that takes the contents of an agreement form that a
    user has submitted and saves it to the database.
    """
    agreement_form_id = request.POST['agreement_form_id']
    project_key = request.POST['project_key']
    agreement_text = request.POST['agreement_text']

    agreement_form = AgreementForm.objects.get(id=agreement_form_id)
    project = DataProject.objects.get(project_key=project_key)

    # Only create a new record if one does not already exist in a state other than Rejected.
    existing_signed_form = SignedAgreementForm.objects.filter(
        user=request.user,
        agreement_form=agreement_form,
        project=project,
    ).exclude(
        status=SIGNED_FORM_REJECTED
    )

    if existing_signed_form.exists():
        logger.debug('%s already has signed the agreement form "%s" for project "%s".', request.user.email, agreement_form.name, project.project_key)
        return HttpResponse(status=400)

    # Check if this agreement form has a specified form class
    fields = {}
    if agreement_form.form_class:
        try:
            form = agreement_form.form(
                request=request,
                project=project,
                data=request.POST,
            )

            # Check validity
            if not form.is_valid():
                logger.debug(form.errors.as_json())

                # Setup the script run.
                response = HttpResponse(content=form.errors.as_json(), status=400)
                response['X-IC-Script'] = "notify('{}', '{}', 'glyphicon glyphicon-{}');".format(
                    "warning", f"The agreement form contained errors, please review", "warning-sign"
                )
                return response

            # Use the data from the form
            fields = form.cleaned_data

        except Exception as e:
            logger.exception(f"Agreement form error: {e}", exc_info=True)
            return HttpResponse(status=500)

    else:
        try:
            # Set fields that we do not need to persist here
            exclusions = [
                "csrfmiddlewaretoken", "project_key", "agreement_form_id",
                "agreement_text"
            ]

            # Save form fields
            for key, value in dict(request.POST.lists()).items():

                # Check exclusions
                if key.lower() in exclusions:
                    continue

                # Retain lists
                if len(value) > 1:

                    # Only retain valid values
                    valid_values = [v for v in value if v]
                    fields[key] = valid_values if valid_values else ""
                else:
                    fields[key] = next(iter(value), "")

        except Exception as e:
            logger.exception(
                f"HYP/Projects/API: Fields error: {e}",
                exc_info=True,
                extra={"form": agreement_form.short_name, "fields": request.POST,}
            )

    signed_agreement_form = SignedAgreementForm(
        user=request.user,
        agreement_form=agreement_form,
        project=project,
        date_signed=datetime.now(),
        agreement_text=agreement_text,
        fields=fields,
    )

    try:
        # Check for a template
        if agreement_form.template:

            # Convert hypens to underscore in context
            safe_fields = {k.replace("-", "_"):v for k,v in fields.items()}

            # Render content of the agreement form
            signed_agreement_form_content = loader.render_to_string(
                template_name=agreement_form.form_file_path,
                context=safe_fields,
            )

            try:
                # Attempt to load PDF template
                loader.get_template(agreement_form.template)

                # Set the filename
                filename = f"{agreement_form.short_name}-{request.user.email}-{datetime.now().isoformat()}.pdf"

                # Set context
                context = {
                    "content": signed_agreement_form_content
                }

                # Submit consent PDF
                logger.debug(f"Rendering agreement form with template: {agreement_form.template}")
                response = render_pdf(filename, request, agreement_form.template, context=context, options={})
                signed_agreement_form.document = ContentFile(response.content, name=filename)

            except TemplateDoesNotExist:
                logger.exception(f"Agreement form template not found: {agreement_form.template}", extra={
                    "agreement_form": agreement_form,
                    "signed_agreement_form": signed_agreement_form,
                })
            except Exception as e:
                logger.exception(f"Document could not be created: {e}", extra={
                    "agreement_form": agreement_form,
                    "signed_agreement_form": signed_agreement_form,
                })

    except Exception as e:
        logger.exception(
            f"HYP/Projects/API: Fields error: {e}",
            exc_info=True,
            extra={"form": agreement_form.short_name, "fields": request.POST,}
        )

    # Save the agreement form
    signed_agreement_form.save()

    # Check for a handler
    if agreement_form.handler:
        try:
            # Build function components
            module_name, handler_name = agreement_form.handler.rsplit('.', 1)
            module = importlib.import_module(module_name)

            # Call handler
            getattr(module, handler_name)(signed_agreement_form)
            logger.debug(f"Handler '{agreement_form.handler}' called for SignedAgreementForm")

        except Exception as e:
            logger.exception(f"Error calling handler: {e}", exc_info=True)

    return HttpResponse(status=200)

@user_auth_and_jwt
def save_signed_external_agreement_form(request):
    """
    An HTTP POST endpoint used to mark when someone has accessed an external agreement form.

    We cannot track if someone has signed a form on an external website, but we can at least
    track that they have clicked the link to visit that website. With this record created,
    an administrator can then manually verify the form on that external site and track their
    approval within Hypatio.
    """

    agreement_form_id = request.POST['agreement_form_id']
    project_key = request.POST['project_key']

    agreement_form = AgreementForm.objects.get(id=agreement_form_id)
    project = DataProject.objects.get(project_key=project_key)

    # Only create a new record if one does not already exist
    try:
        signed_form = SignedAgreementForm.objects.get(
            user=request.user,
            agreement_form=agreement_form,
            project=project
        )
    except ObjectDoesNotExist:
        agreement_text = 'The Participant accessed this form via the 3rd party website. Check there if signed appropriately.'
        signed_agreement_form = SignedAgreementForm(
            user=request.user,
            agreement_form=agreement_form,
            project=project,
            date_signed=datetime.now(),
            agreement_text=agreement_text
        )
        signed_agreement_form.save()

    return HttpResponse(200)

@user_auth_and_jwt
def submit_user_permission_request(request):
    """
    An HTTP POST endpoint to handle a request by a user that wants to access a project.
    Should only be used for projects that do not require teams but do require authorization.
    """

    try:
        project_key = request.POST.get('project_key', None)
        project = DataProject.objects.get(project_key=project_key)
    except ObjectDoesNotExist:
        # Create the response.
        response = HttpResponse(status=404)

        # Setup the script run.
        response['X-IC-Script'] = "notify('{}', '{}', 'glyphicon glyphicon-{}');".format(
            "danger", "The requested project could not be found", "warning-sign"
        )

        return response

    if project.has_teams or not project.requires_authorization:

        # Create the response.
        response = HttpResponse(status=400)

        # Setup the script run.
        response['X-IC-Script'] = "notify('{}', '{}', 'glyphicon glyphicon-{}');".format(
            "danger", "The action could not be completed", "warning-sign"
        )

        return response

    # Create a new participant record if one does not exist already.
    participant, created = Participant.objects.get_or_create(
        user=request.user,
        project=project
    )

    # Check if this project allows institutional signers
    if project.institutional_signers:

        # Check if this is a member
        try:
            official = InstitutionalOfficial.objects.get(
                project=project,
                member_emails__contains=request.user.email,
            )

            # Check if they have access
            official_participant = Participant.objects.get(user=official.user)
            if official_participant.permission == "VIEW":

                # Approve signed agreement forms
                for signed_agreement_form in SignedAgreementForm.objects.filter(project=project, user=request.user):

                    # If allows institutional signers, auto-approve
                    if signed_agreement_form.agreement_form.institutional_signers:

                        signed_agreement_form.status = "A"
                        signed_agreement_form.save()

                # Grant this user access immediately if all agreement forms are accepted
                for agreement_form in project.agreement_forms.all():
                    if not SignedAgreementForm.objects.filter(
                        agreement_form=agreement_form,
                        project=project,
                        user=request.user,
                        status="A"
                        ):
                        break
                else:
                    participant.permission = "VIEW"
                    participant.save()

        except ObjectDoesNotExist:
            pass

    # Check if there are administrators to notify.
    if project.project_supervisors and not participant.permission:

        # Convert the comma separated string of emails into a list.
        supervisor_emails = project.project_supervisors.split(",")

        subject = "DBMI Data Portal - Access requested to dataset"

        email_context = {
            'subject': subject,
            'project': project,
            'user_email': request.user.email,
            'site_url': settings.SITE_URL
        }

        try:
            email_success = email_send(
                subject=subject,
                recipients=supervisor_emails,
                email_template='email_access_request_notification',
                extra=email_context
            )
        except Exception as e:
            logger.exception(e)

    elif participant.permission:
        logger.debug(f"Request has been auto-approved due to an institutional signer")
    else:
        logger.warning(f"Project '{project}' has not supervisors to alert on access requests")

    # Set context
    context = {
        "panel": {
            "additional_context": {
                "requested_access": True,
            }
        }
    }

    # Render the panel and return it
    content = loader.render_to_string("projects/signup/request-access.html", context=context)

    # Create the response.
    response = HttpResponse(content, status=201)

    # Setup the script run.
    response['X-IC-Script'] = "notify('{}', '{}', 'glyphicon glyphicon-{}');".format(
        "success", "Your request for access has been submitted", "thumbs-up"
    )

    # Reload page if approved
    if participant.permission == "VIEW":
        response['X-IC-Script'] += "setTimeout(function() { location.reload(); }, 2000);"

    return response


@user_auth_and_jwt
def upload_signed_agreement_form(request):
    """
    An HTTP POST endpoint that takes the contents of an agreement form that a
    user has submitted and saves it to the database.
    """
    logger.debug(f"[upload_signed_agreement_form]: POST -> {request.POST}")
    logger.debug(f"[upload_signed_agreement_form]: FILES -> {request.FILES}")

    upload = request.FILES['upload']
    agreement_form_id = request.POST['agreement_form_id']
    project_key = request.POST['project_key']
    agreement_text = request.POST['agreement_text']

    agreement_form = AgreementForm.objects.get(id=agreement_form_id)
    project = DataProject.objects.get(project_key=project_key)

    # Only create a new record if one does not already exist in a state other than Rejected.
    existing_signed_form = SignedAgreementForm.objects.filter(
        user=request.user,
        agreement_form=agreement_form,
        project=project,
    ).exclude(
        status=SIGNED_FORM_REJECTED
    )

    if existing_signed_form.exists():
        logger.debug('%s already has signed the agreement form "%s" for project "%s".', request.user.email, agreement_form.name, project.project_key)
        return HttpResponse(status=400)

    signed_agreement_form = SignedAgreementForm(
        user=request.user,
        agreement_form=agreement_form,
        project=project,
        date_signed=datetime.now(),
        upload=upload
    )
    signed_agreement_form.save()

    return HttpResponse(status=200)

@user_auth_and_jwt
def update_institutional_members(request):
    """
    A view for updating the list of members that an institutional official
    providers signing authority for.
    """
    # Get the signed agreement form
    signed_agreement_form_id = request.POST.get("signed-agreement-form")
    official = None
    try:
        # Fetch the official
        official = InstitutionalOfficial.objects.get(user=request.user, signed_agreement_form__id=signed_agreement_form_id)
    except ObjectDoesNotExist:
        logger.debug(f"No InstitutionalOfficial found for '{request.user.email}'")

        # Create the response.
        response = HttpResponse(status=404)

        # Setup the script run.
        response['X-IC-Script'] = "notify('{}', '{}', 'glyphicon glyphicon-{}');".format(
            "danger", "An error occurred during the update. Please try again or contact support", "exclamation-sign"
        )

        return response

    # Get the list
    member_emails = [m.lower() for m in request.POST.getlist("member-emails", [])]

    # Get deletions and additions
    deleted_member_emails = list(set(official.member_emails) - set(member_emails))
    added_member_emails = list(set(member_emails) - set(official.member_emails))

    # Check for duplicates
    if len(set(member_emails)) < len(member_emails):

        # Create the response.
        response = HttpResponse(status=400)

        # Setup the script run.
        response['X-IC-Script'] = "notify('{}', '{}', 'glyphicon glyphicon-{}');".format(
            "warning", "Duplicate email addresses are not allowed", "exclamation-sign"
        )

        return response

    # Save the official with updated emails
    official.member_emails = member_emails
    official.save()

    # Iterate removed emails and remove access
    for email in deleted_member_emails:
        try:
            participant = Participant.objects.get(project=official.project, user__email=email, permission="VIEW")

            # Revoke it if found
            participant.permission = None
            participant.save()

        except ObjectDoesNotExist:
            pass

    # Iterate added emails and add access if waiting
    for email in added_member_emails:
        try:
            official_participant = Participant.objects.get(project=official.project, user=official.user)
            participant = Participant.objects.get(project=official.project, user__email=email)

            # Add access if found
            participant.permission = official_participant.permission
            participant.save()

        except ObjectDoesNotExist:
            pass

    # Create the response.
    response = HttpResponse(status=201)

    # Setup the script run.
    response['X-IC-Script'] = "notify('{}', '{}', 'glyphicon glyphicon-{}');".format(
        "success", "Institutional members updated", "thumbs-up"
    )

    return response
