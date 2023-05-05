import logging
from datetime import datetime
from hypatio.auth0authenticate import user_auth_and_jwt

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Count
from django.db.models import F
from django.db.models import Q
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.contrib import messages
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from django.views.generic.base import View
from django.core.paginator import Paginator
from django.urls import reverse
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from dbmi_client import fileservice

from hypatio.sciauthz_services import SciAuthZ
from hypatio.scireg_services import get_user_profile, get_distinct_countries_participating

from manage.forms import NotificationForm
from manage.models import ChallengeTaskSubmissionExport
from manage.forms import UploadSignedAgreementFormForm
from projects.models import AgreementForm, ChallengeTaskSubmission
from projects.models import DataProject
from projects.models import Participant
from projects.models import Team
from projects.models import TeamComment
from projects.models import SignedAgreementForm
from projects.models import HostedFile
from projects.models import HostedFileDownload
from projects.models import SIGNED_FORM_APPROVED

# Get an instance of a logger
logger = logging.getLogger(__name__)


def is_ajax(request):
    # Returns whether a request is a vanilla ajax request or not
    return request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'


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
        sciauthz = SciAuthZ(user_jwt, self.request.user.email)
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

        self.sciauthz = SciAuthZ(user_jwt, request.user.email)
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

                # Allow hiding of teams
                team_hidden = False

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

                    # If this is a project that is using shared teams, determine if this team should be hidden or not
                    # This is required since shared teams don't implicitly have all forms completed.
                    if self.project.hide_incomplete_teams and self.project.teams_source and not team_hidden:

                        # Get all related signed agreement forms
                        signed_agreement_forms = SignedAgreementForm.objects.filter(
                            Q(user=participant.user, agreement_form__in=self.project.agreement_forms.all()) &
                            (Q(project=self.project) | Q(project__shares_agreement_forms=True))
                        )

                        # Compare number of agreement forms
                        if len(signed_agreement_forms) < len(self.project.agreement_forms.all()):
                            logger.debug(f"{self.project.project_key}/{team.id}/{participant.user.email}: {len(signed_agreement_forms)} SignedAgreementForms: HIDDEN")
                            team_hidden = True

                if not team_hidden:
                    teams.append({
                        'team_leader': team.team_leader.email,
                        'member_count': team.participant_set.all().count(),
                        'status': team.status,
                        'downloads': team_downloads,
                        'submissions': team_uploads,
                    })

            context['teams'] = teams

            approved_teams = list(filter(lambda team: team['status']=='Active', teams))
            approved_participants = Participant.objects.filter(team__in=self.project.team_set.filter(status='Active'))
            all_submissions = ChallengeTaskSubmission.objects.filter(
                participant__in=approved_participants,
                deleted=False
            )
            teams_with_any_submission = all_submissions.values('participant__team').distinct()
            user_jwt = self.request.COOKIES.get("DBMI_JWT", None)
            countries = get_distinct_countries_participating(user_jwt, approved_participants, self.project.project_key)

            context["approved_teams"] = approved_teams
            context["approved_participants"] = approved_participants
            context["total_submissions"] = all_submissions
            context["teams_with_any_submission"] = teams_with_any_submission
            context["participating_countries"] = countries


        # Collect all submissions made for tasks related to this project.
        context['submissions'] = ChallengeTaskSubmission.objects.filter(
            challenge_task__in=self.project.challengetask_set.all(),
            deleted=False
        )

        # Collect all submissions made for tasks related to this project.
        for export in ChallengeTaskSubmissionExport.objects.filter(
            data_project=self.project,
        ).order_by("-request_date"):
            export.download_url = fileservice.get_archivefile_proxy_url(uuid=export.uuid)

            # Add it to context
            context.setdefault('submissions_exports', []).append(export)

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
        elif order_column == 6 and not project.has_teams or order_column == 7 and project.has_teams:
            sort_order = ['modified', 'user__email'] if order_direction == 'asc' else ['-modified', '-user__email']
        else:
            sort_order = ['user__email'] if order_direction == 'asc' else ['-user__email']

        # Get the entire list of current Project Participants
        query_set = project.participant_set.order_by(*sort_order)

        # Setup paginator
        paginator = Paginator(
            query_set.filter(user__email__icontains=search) if search else query_set,
            length
        )

        # Determine page index (1-index) from DT parameters
        page = start / length + 1
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

                # Check if this project uses shared agreement forms
                if project.shares_agreement_forms:

                    # Fetch without a specific project
                    signed_form = SignedAgreementForm.objects.filter(
                        user__email=participant.user.email,
                        agreement_form=agreement_form,
                    ).last()

                else:

                    # Fetch only for this project
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
                        'name': f.agreement_form.short_name,
                        'project': f.project.project_key,
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
                participant.modified,
            ]

            # If project has teams, add that
            if project.has_teams:
                participant_row.insert(1, participant.team.team_leader.email.lower() if participant.team and participant.team.team_leader else '')

            participants.append(participant_row)

        # Build DataTables response data
        data = {
            'draw': draw,
            'recordsTotal': query_set.count(),
            'recordsFiltered': paginator.count,
            'data': participants,
            'error': None,
        }

        return JsonResponse(data=data)


@method_decorator(user_auth_and_jwt, name='dispatch')
class ProjectPendingParticipants(View):

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

        # Check what we're sorting by and in what direction
        if order_column == 0:
            sort_order = ['email'] if order_direction == 'asc' else ['-email']
        elif order_column == 3 and not project.has_teams or order_column == 4 and project.has_teams:
            sort_order = ['modified', '-email'] if order_direction == 'asc' else ['-modified', 'email']
        else:
            sort_order = ['modified', '-email'] if order_direction == 'asc' else ['-modified', 'email']

        # Build the query

        # Find users with all agreement forms approved, but waiting final grant of access
        participants_waiting_access = Participant.objects.filter(Q(project=project, permission__isnull=True))
        for agreement_form in project.agreement_forms.all():

            # Filter by the presence of this agreement form in either a pending or accepted state
            agreement_form_query = Q(
                user__signedagreementform__agreement_form=agreement_form,
                user__signedagreementform__status="A",
            )

            # Ensure the agreement form is for this project or a project that shares agreement forms
            agreement_form_query &= (
                Q(user__signedagreementform__project=project) |
                Q(user__signedagreementform__project__shares_agreement_forms=True)
            )

            # Filter
            participants_waiting_access = participants_waiting_access.filter(agreement_form_query)

        # Secondly, we want Participants with at least one pending SignedAgreementForm
        participants_awaiting_approval = Participant.objects.filter(Q(project=project, permission__isnull=True)).filter(
            Q(
                user__signedagreementform__agreement_form__in=project.agreement_forms.all(),
                user__signedagreementform__status="P",
            ) & (
                Q(user__signedagreementform__project=project) |
                Q(user__signedagreementform__project__shares_agreement_forms=True)
            )
        )

        # Add search if necessary
        if search:
            participants_waiting_access = participants_waiting_access.filter(user__email__icontains=search)
            participants_awaiting_approval = participants_awaiting_approval.filter(user__email__icontains=search)

        # We only want distinct Participants belonging to the users query
        # Django won't sort on a related field after this union so we annotate each queryset with the user's email to sort on
        query_set = participants_waiting_access.annotate(email=F("user__email")) \
            .union(participants_awaiting_approval.annotate(email=F("user__email"))) \
            .order_by(*sort_order)

        # Setup paginator
        paginator = Paginator(
            query_set,
            length,
        )

        # Determine page index (1-index) from DT parameters
        page = start / length + 1
        participant_page = paginator.page(page)

        participants = []
        for participant in participant_page:

            signed_agreement_forms = []
            signed_accepted_agreement_forms = 0

            # For each of the available agreement forms for this project, display only latest version completed by the user
            for agreement_form in project.agreement_forms.all():

                # Check if this project uses shared agreement forms
                if project.shares_agreement_forms:

                    # Fetch without a specific project
                    signed_form = SignedAgreementForm.objects.filter(
                        user__email=participant.user.email,
                        agreement_form=agreement_form,
                    ).last()

                else:

                    # Fetch only for this project
                    signed_form = SignedAgreementForm.objects.filter(
                        user__email=participant.user.email,
                        project=project,
                        agreement_form=agreement_form
                    ).last()

                if signed_form is not None:
                    signed_agreement_forms.append(signed_form)

                    # Collect how many forms are approved to craft language for status
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
                        'name': f.agreement_form.short_name,
                        'project': f.project.project_key,
                    } for f in signed_agreement_forms
                ],
                {
                    'access': True if participant.permission == 'VIEW' else False,
                    'email': participant.user.email.lower(),
                    'signed': signed_accepted_agreement_forms,
                    'team': True if project.has_teams else False,
                    'required': project.agreement_forms.count()
                },
                participant.modified,
            ]

            # If project has teams, add that
            if project.has_teams:
                participant_row.insert(1, participant.team.team_leader.email.lower() if participant.team and participant.team.team_leader else '')

            participants.append(participant_row)

        # Build DataTables response data
        data = {
            'draw': draw,
            'recordsTotal': query_set.count(),
            'recordsFiltered': paginator.count,
            'data': participants,
            'error': None,
        }

        return JsonResponse(data=data)


@user_auth_and_jwt
def team_notification(request, project_key=None):
    """
    Manages sending notifications to team leaders

    :param request: The current HTTP request
    :type request: HttpRequest
    """
    # If this is a POST request we need to process the form data.
    if request.method == 'POST':
        logger.debug(f"Team notification: POST")

        # Process the form.
        form = NotificationForm(request.POST)
        if form.is_valid():

            # Get the project
            project = form.cleaned_data['project']
            team = form.cleaned_data['team']

            # Form the context.
            context = {
                'administrator_message': form.cleaned_data['message'],
                'project': project,
                'team': team,
                'site_url': settings.SITE_URL
            }

            # Send it out.
            email_template='team_notification'
            subject='DBMI Portal - Team Notification'

            # Render templates
            msg_html = render_to_string('email/email_team_notification.html', context)
            msg_plain = render_to_string('email/email_team_notification.txt', context)

            try:
                msg = EmailMultiAlternatives(subject=subject,
                                            body=msg_plain,
                                            from_email=settings.DEFAULT_FROM_EMAIL,
                                            to=[team.team_leader.email])
                msg.attach_alternative(msg_html, "text/html")
                msg.send()

                # Handle outcome
                if is_ajax(request):
                    return HttpResponse('SUCCESS', status=200)
                else:
                    # Set a message.
                    messages.success(request, 'Thanks, your notification has been sent!')

            except Exception as ex:
                logger.exception(ex, exc_info=True, extra={
                    'email': email_template, 'extra': context
                })

                # Check how the request was made.
                if is_ajax(request):
                    return HttpResponse('ERROR', status=500)
                else:
                    messages.error(request, 'An unexpected error occurred, please try again')

                    # Send them back
                    return HttpResponseRedirect(reverse(
                        'projects:view-project',
                        kwargs={'project_key': form.cleaned_data['project']}
                    ))
        else:
            logger.error(f"Invalid team notification form", extra={
                'request': request, 'errors': form.errors.as_json(),
            })

            # Check how the request was made.
            if is_ajax(request):
                return HttpResponse(form.errors.as_json(), status=500)
            else:
                messages.error(request, 'The form was invalid, please try again')
                return HttpResponseRedirect(reverse(
                    'projects:view-project',
                    kwargs={'project_key': form.cleaned_data['project']}
                ))

    logger.debug(f"Team notification: GET")

    # If a GET (or any other method) we'll create a blank form.
    initial = {}

    # If a project key was supplied and it matches a real project, pre-populate the form with it.
    try:
        if project_key:
            data_project = DataProject.objects.get(project_key=project_key)
        else:
            data_project = DataProject.objects.get(id=request.GET["project"])

        initial['project'] = data_project
    except ObjectDoesNotExist:
        logger.exception(f"Could not determine project", exc_info=True, extra={
            'request': request,
        })
        if is_ajax(request):
            return HttpResponse('The project could not be determined, cannot send message.', status=500)
        else:
            messages.error(request, 'The project could not be determined, cannot send message.')

    # Get the team
    try:
        team = Team.objects.get(id=request.GET["team"])
        initial['team'] = team
    except ObjectDoesNotExist:
        logger.exception(f"Could not determine team leader", exc_info=True, extra={
            'request': request,
        })
        if is_ajax(request):
            return HttpResponse('The team leader could not be determined, cannot send message.', status=500)
        else:
            messages.error(request, 'The team leader could not be determined, cannot send message.')

    # Generate and render the form.
    form = NotificationForm(initial=initial)
    return render(request, 'manage/notification.html', {'notification_form': form})


@user_auth_and_jwt
def manage_team(request, project_key, team_leader, template_name='manage/team.html'):
    """
    Populates the team management screen.
    """

    user = request.user
    user_jwt = request.COOKIES.get("DBMI_JWT", None)

    sciauthz = SciAuthZ(user_jwt, user.email)
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

        # Check if this participant has access
        access_granted = member.permission == "VIEW"

        signed_agreement_forms = []
        signed_accepted_agreement_forms = 0

        # For each of the available agreement forms for this project, display only latest version completed by the user
        for agreement_form in project.agreement_forms.all():

            # If this project accepts agreement forms from other projects, check those
            if project.shares_agreement_forms:

                # Fetch without a specific project
                signed_form = SignedAgreementForm.objects.filter(
                    user__email=email,
                    agreement_form=agreement_form,
                ).last()

            else:
                # Fetch only for the current project
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

            # Add internal signed agreement forms
            for signed_agreement_form in SignedAgreementForm.objects.filter(
                agreement_form__internal=True,
                user__email=email,
                project=project):

                    # Add it
                    signed_agreement_forms.append(signed_agreement_form)

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


@method_decorator([user_auth_and_jwt], name='dispatch')
class UploadSignedAgreementFormView(View):
    """
    View to upload signed agreement forms for participants.

    * Requires token authentication.
    * Only admin users are able to access this view.
    """
    def get(self, request, project_key, user_email, *args, **kwargs):
        """
        Return the upload form template
        """
        user = request.user
        user_jwt = request.COOKIES.get("DBMI_JWT", None)

        sciauthz = SciAuthZ(user_jwt, user.email)
        is_manager = sciauthz.user_has_manage_permission(project_key)

        if not is_manager:
            logger.debug('User {email} does not have MANAGE permissions for item {project_key}.'.format(
                email=user.email,
                project_key=project_key
            ))
            return HttpResponse(403)

        # Return file upload form
        form = UploadSignedAgreementFormForm(initial={
            "project_key": project_key,
            "participant": user_email,
        })

        # Set context
        context = {
            "form": form,
            "project_key": project_key,
            "user_email": user_email,
        }

        # Render html
        return render(request, "manage/upload-signed-agreement-form.html", context)

    def post(self, request, project_key, user_email, *args, **kwargs):
        """
        Process the form
        """
        user = request.user
        user_jwt = request.COOKIES.get("DBMI_JWT", None)

        sciauthz = SciAuthZ(user_jwt, user.email)
        is_manager = sciauthz.user_has_manage_permission(project_key)

        if not is_manager:
            logger.debug('User {email} does not have MANAGE permissions for item {project_key}.'.format(
                email=user.email,
                project_key=project_key
            ))
            return HttpResponse(403)

        # Assembles the form and run validation.
        form = UploadSignedAgreementFormForm(data=request.POST, files=request.FILES)
        if not form.is_valid():
            logger.warning('Form failed: {}'.format(form.errors.as_json()))
            return HttpResponse(status=400)

        logger.debug(f"[upload_signed_agreement_form] Data -> {form.cleaned_data}")

        signed_agreement_form = form.cleaned_data['signed_agreement_form']
        agreement_form = form.cleaned_data['agreement_form']
        project_key = form.cleaned_data['project_key']
        participant_email = form.cleaned_data['participant']

        project = DataProject.objects.get(project_key=project_key)
        participant = Participant.objects.get(project=project, user__email=participant_email)

        signed_agreement_form = SignedAgreementForm(
            user=participant.user,
            agreement_form=agreement_form,
            project=project,
            date_signed=datetime.now(),
            upload=signed_agreement_form,
            status=SIGNED_FORM_APPROVED,
        )
        signed_agreement_form.save()

        # Create the response.
        response = HttpResponse(status=201)

        # Setup the script run.
        response['X-IC-Script'] = "notify('{}', '{}', 'glyphicon glyphicon-{}');".format(
            "success", "Signed agreement form successfully uploaded", "thumbs-up"
        )

        # Close the modal
        response['X-IC-Script'] += "$('#page-modal').modal('hide');"

        return response
