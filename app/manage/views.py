import json
import logging

from pyauth0jwt.auth0authenticate import user_auth_and_jwt

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

from hypatio.sciauthz_services import SciAuthZ
from hypatio.scireg_services import get_distinct_countries_participating
from hypatio.scireg_services import get_user_profile
from hypatio.scireg_services import get_names

from projects.models import DataProject
from projects.models import Team
from projects.models import TeamComment
from projects.models import AgreementForm
from projects.models import SignedAgreementForm
from projects.models import HostedFile
from projects.models import HostedFileDownload
from projects.models import Participant
from projects.models import ChallengeTaskSubmission

# Get an instance of a logger
logger = logging.getLogger(__name__)

@method_decorator(user_auth_and_jwt, name='dispatch')
class DataProjectManageView(TemplateView):
    """
    Builds and renders the screen for special users to manage a DataProject.
    """

    project = None
    template_name = 'manage/base.html'

    def dispatch(self, request, *args, **kwargs):
        """
        Sets up the instance.
        """

        # Get the project key from the URL.
        project_key = self.kwargs['project_key']

        try:
            self.project = DataProject.objects.get(project_key=project_key)
        except ObjectDoesNotExist:
            error_message = "The project you searched for does not exist."
            return render(request, '404.html', {'error_message': error_message})

        user_jwt = request.COOKIES.get("DBMI_JWT", None)

        sciauthz = SciAuthZ(settings.AUTHZ_BASE, user_jwt, request.user.email)
        is_manager = sciauthz.user_has_manage_permission(project_key)

        if not is_manager:
            logger.debug(
                '[HYPATIO][DEBUG][DataProjectManageView] User {email} does not have MANAGE permissions for item {project_key}.'.format(
                    email=request.user.email,
                    project_key=project_key
                )
            )
            return HttpResponse("Unauthorized", status=403)

        return super(DataProjectManageView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """
        Dynamically builds the context for rendering the view based on information
        about the user and the DataProject.
        """

        # Get super's context. This is the dictionary of variables for the base template being rendered.
        context = super(DataProjectManageView, self).get_context_data(**kwargs)

        context['project'] = self.project

        return context

@user_auth_and_jwt
def manage_team(request, project_key, team_leader, template_name='manage/team.html'):
    """
    Populates the team management screen.
    """

    user = request.user
    user_jwt = request.COOKIES.get("DBMI_JWT", None)

    sciauthz = SciAuthZ(settings.AUTHZ_BASE, user_jwt, user.email)
    is_manager = sciauthz.user_has_manage_permission(project_key)
    has_manage_permissions = sciauthz.user_has_any_manage_permissions()

    if not is_manager:
        logger.debug(
            '[HYPATIO][DEBUG][manage_team] User ' + user.email + ' does not have MANAGE permissions for item ' + project_key + '.')
        return HttpResponse(403)

    project = DataProject.objects.get(project_key=project_key)
    team = Team.objects.get(data_project=project, team_leader__email=team_leader)
    num_required_forms = project.agreement_forms.count()

    # Collect all the team member information needed
    team_member_details = []
    team_participants = team.participant_set.all()
    team_accepted_forms = 0

    for member in team_participants:
        email = member.user.email

        # Make a request to SciReg for a specific person's user information
        user_info_json = get_user_profile(user_jwt, email, project_key)

        if user_info_json['count'] != 0:
            user_info = user_info_json["results"][0]
        else:
            user_info = None

        signed_agreement_forms = []
        signed_accepted_agreement_forms = 0

        # For each of the available agreement forms for this project, display only latest version completed by the user
        for agreement_form in project.agreement_forms.all():
            signed_form = SignedAgreementForm.objects.filter(user__email=email,
                                                             project=project,
                                                             agreement_form=agreement_form).last()

            if signed_form is not None:
                signed_agreement_forms.append(signed_form)

                if signed_form.status == 'A':
                    team_accepted_forms += 1
                    signed_accepted_agreement_forms += 1

        team_member_details.append({
            'email': email,
            'user_info': user_info,
            'signed_agreement_forms': signed_agreement_forms,
            'signed_accepted_agreement_forms': signed_accepted_agreement_forms,
            'participant': member
        })

    # Check whether this team has completed all the necessary forms and they have been accepted by challenge admins
    total_required_forms_for_team = project.agreement_forms.count() * team_participants.count()
    team_has_all_forms_complete = total_required_forms_for_team == team_accepted_forms

    institution = project.institution

    # Get the comments made about this team by challenge administrators
    comments = TeamComment.objects.filter(team=team)

    # Get a history of files downloaded and uploaded by members of this team
    files = HostedFile.objects.filter(project=project)
    team_users = User.objects.filter(participant__in=team_participants)
    downloads = HostedFileDownload.objects.filter(hosted_file__in=files, user__in=team_users)
    uploads = team.get_submissions()

    return render(request, template_name, context={"user": user,
                                                   "ssl_setting": settings.SSL_SETTING,
                                                   "has_manage_permissions": has_manage_permissions,
                                                   "project": project,
                                                   "team": team,
                                                   "team_members": team_member_details,
                                                   "num_required_forms": num_required_forms,
                                                   "team_has_all_forms_complete": team_has_all_forms_complete,
                                                   "institution": institution,
                                                   "comments": comments,
                                                   "downloads": downloads,
                                                   "uploads": uploads})

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