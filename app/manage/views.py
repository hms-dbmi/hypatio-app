import logging

from pyauth0jwt.auth0authenticate import user_auth_and_jwt

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

from hypatio.sciauthz_services import SciAuthZ
from hypatio.scireg_services import get_user_profile

from projects.models import ChallengeTask
from projects.models import ChallengeTaskSubmission
from projects.models import DataProject
from projects.models import Team
from projects.models import TeamComment
from projects.models import SignedAgreementForm
from projects.models import HostedFile
from projects.models import HostedFileDownload

# Get an instance of a logger
logger = logging.getLogger(__name__)

@method_decorator(user_auth_and_jwt, name='dispatch')
class DataProjectListManageView(TemplateView):
    """
    Builds and renders a screen for users to select which project they want to
    enter the management screen for. Only displays the projects that they have
    MANAGE permissions for.
    """

    template_name = 'manage/project-list.html'

    def dispatch(self, request, *args, **kwargs):
        """
        Sets up the instance.
        """

        return super(DataProjectListManageView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """
        Dynamically builds the context for rendering the view based on information
        about the user and the DataProject.
        """

        # Get super's context. This is the dictionary of variables for the base template being rendered.
        context = super(DataProjectListManageView, self).get_context_data(**kwargs)

        user_jwt = self.request.COOKIES.get("DBMI_JWT", None)
        sciauthz = SciAuthZ(settings.AUTHZ_BASE, user_jwt, self.request.user.email)
        projects_managed = sciauthz.get_projects_managed_by_user()

        context['projects'] = projects_managed

        return context

@method_decorator(user_auth_and_jwt, name='dispatch')
class DataProjectManageView(TemplateView):
    """
    Builds and renders the screen for special users to manage a DataProject.
    """

    project = None
    template_name = 'manage/project-base.html'
    sciauthz = None

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

        self.sciauthz = SciAuthZ(settings.AUTHZ_BASE, user_jwt, request.user.email)
        is_manager = self.sciauthz.user_has_manage_permission(project_key)

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

        # Collect all permissions people have for this project.
        users_with_view_permissions = self.sciauthz.get_all_view_permissions_for_project(self.project.project_key)

        # Collect all user information from SciReg.
        # TODO ...

        # Get counts of downloads by isolating which files this project has, grouping by user email, and counting on those emails.
        user_download_counts = HostedFileDownload.objects\
            .filter(hosted_file__project=self.project)\
            .values('user__email')\
            .annotate(user_downloads=Count('user__email'))

        # Get how many challengetasks a user has submitted for this project.
        user_upload_counts = ChallengeTaskSubmission.objects\
            .filter(challenge_task__data_project=self.project)\
            .values('participant__user__email')\
            .annotate(user_uploads=Count('participant__user__email'))

        participants = []
        for participant in self.project.participant_set.all():

            try:
                download_count = user_download_counts.get(user__email=participant.user.email)['user_downloads']
            except ObjectDoesNotExist:
                download_count = 0

            try:
                upload_count = user_upload_counts.get(participant__user__email=participant.user.email)['user_uploads']
            except ObjectDoesNotExist:
                upload_count = 0

            signed_agreement_forms = []

            # For each of the available agreement forms for this project, display only latest version completed by the user
            for agreement_form in self.project.agreement_forms.all():
                signed_form = SignedAgreementForm.objects.filter(
                    user__email=participant.user.email,
                    project=self.project,
                    agreement_form=agreement_form
                ).last()

                if signed_form is not None:
                    signed_agreement_forms.append(signed_form)

            participants.append({
                'participant': participant,
                'view_permissions': True if participant.user.email.lower() in users_with_view_permissions else False,
                'download_count': download_count,
                'upload_count': upload_count,
                'signed_forms': signed_agreement_forms
            })

        context['participants'] = participants

        # If there are teams, calculate downloads and uploads by team members.
        if self.project.has_teams:

            teams = []
            for team in self.project.team_set.all():

                team_downloads = 0
                team_uploads = 0

                for participant in team.participant_set.all():
                    try:
                        team_downloads += user_download_counts.get(user__email=participant.user.email)['user_downloads']
                    except ObjectDoesNotExist:
                        team_downloads += 0

                    try:
                        team_uploads += user_upload_counts.get(participant__user__email=participant.user.email)['user_uploads']
                    except ObjectDoesNotExist:
                        team_uploads += 0

                teams.append({
                    'team_leader': team.team_leader.email,
                    'member_count': team.participant_set.all().count(),
                    'status': team.status,
                    'downloads': team_downloads,
                    'submissions': team_uploads,
                })

            context['teams'] = teams

        # Collect all submissions made for tasks related to this project.
        context['submissions'] = ChallengeTaskSubmission.objects.filter(
            challenge_task__in=self.project.challengetask_set.all(),
            deleted=False
        )

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

    if not is_manager:
        logger.debug('User {email} does not have MANAGE permissions for item {project_key}.'.format(
            email=user.email,
            project_key=project_key
        ))
        return HttpResponse(403)

    project = DataProject.objects.get(project_key=project_key)
    team = Team.objects.get(data_project=project, team_leader__email=team_leader)
    num_required_forms = project.agreement_forms.count()

    # Collect all the team member information needed.
    team_member_details = []
    team_participants = team.participant_set.all()
    team_accepted_forms = 0

    for member in team_participants:
        email = member.user.email

        # Make a request to DBMIReg to get this person's user information.
        user_info_json = get_user_profile(user_jwt, email, project_key)

        if user_info_json['count'] != 0:
            user_info = user_info_json["results"][0]
        else:
            user_info = None

        # Make a request to DBMIAuthZ to check for this person's permissions.
        access_granted = sciauthz.user_has_single_permission(project_key, "VIEW", email)

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
            'participant': member,
            'access_granted': access_granted,
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

    context = {
        "user": user,
        "ssl_setting": settings.SSL_SETTING,
        "project": project,
        "team": team,
        "team_members": team_member_details,
        "num_required_forms": num_required_forms,
        "team_has_all_forms_complete": team_has_all_forms_complete,
        "institution": institution,
        "comments": comments,
        "downloads": downloads,
        "uploads": uploads
    }

    return render(request, template_name, context=context)
