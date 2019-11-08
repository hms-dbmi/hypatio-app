import logging

from pyauth0jwt.auth0authenticate import user_auth_and_jwt

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Count
from django.db.models import F
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from django.views.generic.base import View
from django.core.paginator import Paginator

from hypatio.sciauthz_services import SciAuthZ
from hypatio.scireg_services import get_user_profile, get_distinct_countries_participating

from projects.models import ChallengeTaskSubmission
from projects.models import DataProject
from projects.models import Participant
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

        # Collect all user information from SciReg.
        # TODO ...

        # Get counts of downloads by isolating which files this project has, grouping by user email, and counting on those emails.
        user_download_counts = HostedFileDownload.objects\
            .filter(hosted_file__project=self.project)\
            .values('user__email')\
            .annotate(user_downloads=Count('user__email'))

        # Convert the download count queryset into a simple dictionary for quicker access later.
        user_download_counts_dict = {}
        for user in user_download_counts:
            user_download_counts_dict[user['user__email']] = user['user_downloads']

        # Get how many challengetasks a user has submitted for this project.
        user_upload_counts = ChallengeTaskSubmission.objects\
            .filter(challenge_task__data_project=self.project)\
            .values('participant__user__email')\
            .annotate(user_uploads=Count('participant__user__email'))

        # If there are teams, calculate downloads and uploads by team members.
        if self.project.has_teams:

            teams = []
            for team in self.project.team_set.all():

                team_downloads = 0
                team_uploads = 0

                for participant in team.participant_set.all():
                    try:
                        team_downloads += user_download_counts_dict[participant.user.email]
                    except KeyError:
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

            approved_teams = list(filter(lambda team: team['status'] is 'Active', teams))
            participants = Participant.objects.filter(team__in=approved_teams)
            approved_participants = list(filter(lambda participant: participant.team in approved_teams, participants))
            all_submissions = ChallengeTaskSubmission.objects.filter(
                participant__in=approved_participants,
                deleted=False
            )
            teams_with_any_submission = all_submissions.values('participant__team').distinct()
            user_jwt = self.request.COOKIES.get("DBMI_JWT", None)
            countries = get_distinct_countries_participating(user_jwt, approved_participants, self.project.project_key)

            context["approved_teams"] = approved_teams,
            context["approved_participants"] = approved_participants,
            context["total_submissions"] = all_submissions,
            context["teams_with_any_submission"] = teams_with_any_submission,
            context["participating_countries"] = countries,


        # Collect all submissions made for tasks related to this project.
        context['submissions'] = ChallengeTaskSubmission.objects.filter(
            challenge_task__in=self.project.challengetask_set.all(),
            deleted=False
        )

        context['num_required_forms'] = self.project.agreement_forms.count()

        # Get information about what files there are for this project.
        context['file_groups'] = []

        for file_set in self.project.hostedfileset_set.all().order_by(F('order').asc(nulls_last=True)):
            context['file_groups'].append({
                'group_name': file_set.title,
                'files': file_set.hostedfile_set.all().order_by(F('order').asc(nulls_last=True))
            })

        # Add another panel for files that do not belong to a HostedFileSet
        files_without_a_set = HostedFile.objects.filter(
            project=self.project,
            hostedfileset=None
        )

        if files_without_a_set.count() > 0:
            # If there are no other groups, then make the group title less confusing.
            group_name = 'Files' if not context['file_groups'] else 'Other files'

            context['file_groups'].append({
                'group_name': group_name,
                'files': files_without_a_set.order_by(F('order').asc(nulls_last=True))
            })

        return context


@method_decorator(user_auth_and_jwt, name='dispatch')
class ProjectParticipants(View):

    def get(self, request, project_key, *args, **kwargs):

        # Pull the project
        try:
            project = DataProject.objects.get(project_key=project_key)
        except DataProject.NotFound:
            logger.exception('DataProject for key "{}" not found'.format(project_key))
            return HttpResponse(status=404)

        # Get needed params
        draw = int(request.GET['draw'])
        start = int(request.GET['start'])
        length = int(request.GET['length'])
        order_column = int(request.GET['order[0][column]'])
        order_direction = request.GET['order[0][dir]']

        # Check for a search value
        search = request.GET['search[value]']

        # Get counts of downloads by isolating which files this project has, grouping by user email, and counting on those emails.
        user_download_counts = HostedFileDownload.objects \
            .filter(hosted_file__project=project) \
            .values('user__email') \
            .annotate(user_downloads=Count('user__email'))

        # Convert the download count queryset into a simple dictionary for quicker access later.
        user_download_counts_dict = {}
        for user in user_download_counts:
            user_download_counts_dict[user['user__email']] = user['user_downloads']

        # Get how many challengetasks a user has submitted for this project.
        user_upload_counts = ChallengeTaskSubmission.objects \
            .filter(challenge_task__data_project=project) \
            .values('participant__user__email') \
            .annotate(user_uploads=Count('participant__user__email'))

        # Check what we're sorting by and in what direction
        if order_column == 0:
            sort_order = ['user__email'] if order_direction == 'asc' else ['-user__email']
        elif order_column == 3 and not project.has_teams or order_column == 4 and project.has_teams:
            sort_order = ['permission', 'user__email'] if order_direction == 'asc' else ['-permission', '-user__email']
        else:
            sort_order = ['user__email'] if order_direction == 'asc' else ['-user__email']

        # Paginate participants
        query_set = project.participant_set.filter(user__email__icontains=search).order_by(*sort_order).all() \
            if search else project.participant_set.order_by(*sort_order).all()
        paginator = Paginator(query_set, length)

        # Determine page index (1-index) from DT parameters
        page = start / length + 1
        logger.debug('Participant page: {}'.format(page))
        participant_page = paginator.page(page)

        participants = []
        for participant in participant_page:

            try:
                download_count = user_download_counts_dict[participant.user.email]
            except KeyError:
                download_count = 0

            try:
                upload_count = user_upload_counts.get(participant__user__email=participant.user.email)['user_uploads']
            except ObjectDoesNotExist:
                upload_count = 0

            signed_agreement_forms = []
            signed_accepted_agreement_forms = 0

            # For each of the available agreement forms for this project, display only latest version completed by the user
            for agreement_form in project.agreement_forms.all():
                signed_form = SignedAgreementForm.objects.filter(
                    user__email=participant.user.email,
                    project=project,
                    agreement_form=agreement_form
                ).last()

                if signed_form is not None:
                    signed_agreement_forms.append(signed_form)

                    if signed_form.status == 'A':
                        signed_accepted_agreement_forms += 1

            # Build the row of the table for this participant
            participant_row = [
                participant.user.email.lower(),
                'Access granted' if participant.permission == 'VIEW' else 'No access',
                [
                    {
                        'status': f.status,
                        'id': f.id,
                        'name': f.agreement_form.short_name
                    } for f in signed_agreement_forms
                ],
                {
                    'access': True if participant.permission == 'VIEW' else False,
                    'email': participant.user.email.lower(),
                    'signed': signed_accepted_agreement_forms,
                    'team': True if project.has_teams else False,
                    'required': project.agreement_forms.count()
                },
                download_count,
                upload_count,
            ]

            # If project has teams, add that
            if project.has_teams:
                participant_row.insert(1, participant.team.team_leader.email.lower() if participant.team and participant.team.team_leader else '')

            participants.append(participant_row)

        # Build DataTables response data
        data = {
            'draw': draw,
            'recordsTotal': project.participant_set.count(),
            'recordsFiltered': paginator.count,
            'data': participants,
            'error': None,
        }

        return JsonResponse(data=data)


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

    try:
        project = DataProject.objects.get(project_key=project_key)
        team = Team.objects.get(data_project=project, team_leader__email=team_leader)
    except ObjectDoesNotExist:
        return render(request, '404.html')

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
            signed_form = SignedAgreementForm.objects.filter(
                user__email=email,
                project=project,
                agreement_form=agreement_form
            ).last()

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
