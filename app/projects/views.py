import json
import logging
from datetime import datetime

from django.conf import settings
from django.contrib.auth import logout
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from hypatio.sciauthz_services import SciAuthZ
from hypatio.scireg_services import get_current_user_profile
from hypatio.scireg_services import get_user_email_confirmation_status
from hypatio.scireg_services import get_user_profile
from profile.forms import RegistrationForm
from projects.steps.dynamic_form import SignAgreementFormsStepInitializer

from pyauth0jwt.auth0authenticate import logout_redirect
from pyauth0jwt.auth0authenticate import public_user_auth_and_jwt
from pyauth0jwt.auth0authenticate import user_auth_and_jwt
from pyauth0jwt.auth0authenticate import validate_request as validate_jwt
from .models import AgreementForm
from .models import DataProject
from .models import HostedFile
from .models import HostedFileDownload
from .models import Participant
from .models import SignedAgreementForm
from .models import Team
from .models import TeamComment

# Get an instance of a logger
logger = logging.getLogger(__name__)


@user_auth_and_jwt
def signout(request):
    logout(request)
    response = redirect(settings.AUTH0_LOGOUT_URL)
    response.delete_cookie('DBMI_JWT', domain=settings.COOKIE_DOMAIN)
    return response

@user_auth_and_jwt
def request_access(request, template_name='dataprojects/access_request.html'):

    project = DataProject.objects.get(project_key=request.POST['project_key'])
    agreement_forms = project.agreement_forms.all()

    return render(request, template_name, {"project_key": request.POST['project_key'],
                                           "agreement_forms": agreement_forms})


@user_auth_and_jwt
def save_dynamic_signed_agreement_form(request):

    agreement_form_id = request.POST['agreement_form_id']
    project_key = request.POST['project_key']
    model_name = request.POST['model_name']

    return HttpResponse(200)


@user_auth_and_jwt
def save_signed_agreement_form(request):

    agreement_form_id = request.POST['agreement_form_id']
    project_key = request.POST['project_key']
    agreement_text = request.POST['agreement_text']

    agreement_form = AgreementForm.objects.get(id=agreement_form_id)
    project = DataProject.objects.get(project_key=project_key)

    signed_agreement_form = SignedAgreementForm(user=request.user,
                                                agreement_form=agreement_form,
                                                project=project,
                                                date_signed=datetime.now(),
                                                agreement_text=agreement_text)
    signed_agreement_form.save()

    return HttpResponse(200)

@user_auth_and_jwt
def submit_user_permission_request(request):

    user_jwt = request.COOKIES.get("DBMI_JWT", None)

    sciauthz = SciAuthZ(settings.AUTHZ_BASE, user_jwt, request.user.email)

    data_request = {"user": request.user.email,
                    "item": request.POST['project_key']}

    sciauthz.current_user_request_access(data_request)

    return HttpResponse(200)

@user_auth_and_jwt
def signed_agreement_form(request, template_name='shared/signed_agreement_form.html'):

    project_key = request.GET['project_key']
    signed_agreement_form_id = request.GET['signed_form_id']

    user_jwt = request.COOKIES.get("DBMI_JWT", None)
    sciauthz = SciAuthZ(settings.AUTHZ_BASE, user_jwt, request.user.email)
    is_manager = sciauthz.user_has_manage_permission(project_key)

    project = get_object_or_404(DataProject, project_key=project_key)
    signed_form = get_object_or_404(SignedAgreementForm, id=signed_agreement_form_id, project=project)
    participant = Participant.objects.get(data_challenge=project, user=signed_form.user)

    if is_manager or signed_form.user == request.user:
        return render(request, template_name, {"user": request.user,
                                               "ssl_setting": settings.SSL_SETTING,
                                               "is_manager": is_manager,
                                               "signed_form": signed_form,
                                               "participant": participant})
    else:
        return HttpResponse(403)

@public_user_auth_and_jwt
def list_data_projects(request, template_name='dataprojects/list.html'):

    all_data_projects = DataProject.objects.filter(is_contest=False, visible=True)

    data_projects = []
    projects_with_view_permissions = []
    projects_with_access_requests = {}

    is_manager = False

    if not request.user.is_authenticated():
        user = None
    else:
        user = request.user
        user_jwt = request.COOKIES.get("DBMI_JWT", None)

        # If for some reason they have a session but not JWT, force them to log in again.
        if user_jwt is None or validate_jwt(request) is None:
            return logout_redirect(request)

        sciauthz = SciAuthZ(settings.AUTHZ_BASE, user_jwt, user.email)
        is_manager = sciauthz.user_has_manage_permission('n2c2-t1')
        user_permissions = sciauthz.current_user_permissions()
        user_access_requests = sciauthz.current_user_access_requests()

        logger.debug('[HYPATIO][DEBUG] User Permissions: ' + json.dumps(user_permissions))

        if user_permissions is not None and 'results' in user_permissions:
            user_permissions = user_permissions["results"]

            for user_permission in user_permissions:
                if user_permission['permission'] == 'VIEW':
                    projects_with_view_permissions.append(user_permission['item'])

        # Get all of the user's permission requests
        access_requests_url = settings.AUTHORIZATION_REQUEST_URL + "?email=" + user.email

        logger.debug('[HYPATIO][DEBUG] access_requests_url: ' + access_requests_url)
        logger.debug('[HYPATIO][DEBUG] User Permission Requests: ' + json.dumps(user_access_requests))

        if user_access_requests is not None and 'results' in user_access_requests:
            user_access_requests = user_access_requests["results"]

            for access_request in user_access_requests:
                projects_with_access_requests[access_request['item']] = {
                    'date_requested': access_request['date_requested'],
                    'request_granted': access_request['request_granted'],
                    'date_request_granted': access_request['date_request_granted']}

    # Build the dictionary with all project and permission information needed
    for project in all_data_projects:

        project_data_url = None
        user_has_view_permissions = project.project_key in projects_with_view_permissions

        if project.project_key in projects_with_access_requests:
            user_requested_access_on = projects_with_access_requests[project.project_key]['date_requested']
            user_requested_access = True
        else:
            user_requested_access_on = None
            user_requested_access = False

        datagate = project.datagate_set.first()

        if datagate:
            project_data_url = datagate.data_location

        # Package all the necessary information into one dictionary
        project = {"name": project.name,
                   "short_description": project.short_description,
                   "description": project.description,
                   "project_key": project.project_key,
                   "project_url": project_data_url,
                   "permission_scheme": project.permission_scheme,
                   "user_has_view_permissions": user_has_view_permissions,
                   "user_requested_access": user_requested_access,
                   "user_requested_access_on": user_requested_access_on}

        data_projects.append(project)

    return render(request, template_name, {"data_projects": data_projects,
                                           "user": user,
                                           "ssl_setting": settings.SSL_SETTING,
                                           "is_manager": is_manager,
                                           "account_server_url": settings.ACCOUNT_SERVER_URL,
                                           "profile_server_url": settings.SCIREG_SERVER_URL})

@public_user_auth_and_jwt
def list_data_challenges(request, template_name='datacontests/list.html'):

    all_data_contests = DataProject.objects.filter(is_contest=True, visible=True)
    data_contests = []

    is_manager = False

    if not request.user.is_authenticated():
        user = None
    else:

        user = request.user
        user_jwt = request.COOKIES.get("DBMI_JWT", None)

        # If for some reason they have a session but not JWT, force them to log in again.
        if user_jwt is None or validate_jwt(request) is None:
            return logout_redirect(request)

        if request.user.is_superuser:
            all_data_contests = DataProject.objects.filter(is_contest=True)

        sciauthz = SciAuthZ(settings.AUTHZ_BASE, user_jwt, user.email)
        is_manager = sciauthz.user_has_manage_permission('n2c2-t1')

    # Build the dictionary with all project and permission information needed
    for data_contest in all_data_contests:
        logger.debug(data_contest.name)
        
        # Package all the necessary information into one dictionary
        contest = {"name": data_contest.name,
                        "short_description": data_contest.short_description,
                        "description": data_contest.description,
                        "project_key": data_contest.project_key,
                        "permission_scheme": data_contest.permission_scheme}

        data_contests.append(contest)

    return render(request, template_name, {"data_contests": data_contests,
                                           "user": user,
                                           "ssl_setting": settings.SSL_SETTING,
                                           "is_manager": is_manager,
                                           "account_server_url": settings.ACCOUNT_SERVER_URL,
                                           "profile_server_url": settings.SCIREG_SERVER_URL})

@user_auth_and_jwt
def manage_team(request, project_key, team_leader, template_name='datacontests/manageteams.html'):
    """
    Populates the team management modal popup on the contest management screen.
    """

    user = request.user
    user_jwt = request.COOKIES.get("DBMI_JWT", None)

    sciauthz = SciAuthZ(settings.AUTHZ_BASE, user_jwt, user.email)
    is_manager = sciauthz.user_has_manage_permission(project_key)

    if not is_manager:
        logger.debug('[HYPATIO][DEBUG][manage_team] User ' + user.email + ' does not have MANAGE permissions for item ' + project_key + '.')
        return HttpResponse(403)

    project = DataProject.objects.get(project_key=project_key)
    team = Team.objects.get(data_project=project, team_leader__email=team_leader)
    num_required_forms = project.agreement_forms.count()

    user_jwt = request.COOKIES.get("DBMI_JWT", None)

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
                                                   "is_manager": is_manager,
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
def manage_contest(request, project_key, template_name='datacontests/managecontests.html'):

    project = DataProject.objects.get(project_key=project_key)

    # This dictionary will hold all user requests and permissions
    user_details = {}

    user = request.user
    user_jwt = request.COOKIES.get("DBMI_JWT", None)

    sciauthz = SciAuthZ(settings.AUTHZ_BASE, user_jwt, user.email)
    is_manager = sciauthz.user_has_manage_permission(project_key)

    if not is_manager:
        logger.debug('[HYPATIO][DEBUG][manage_contest] User ' + user.email + ' does not have MANAGE permissions for item ' + project_key + '.')
        return HttpResponse(403)

    teams = Team.objects.filter(data_project=project)

    # A person who has filled out a form for a project but not yet joined a team
    users_with_a_team = Participant.objects.filter(team__in=teams).values_list('user', flat=True).distinct()
    users_who_signed_forms = SignedAgreementForm.objects.filter(project=project).values_list('user', flat=True).distinct()
    users_without_a_team = User.objects.filter(id__in=users_who_signed_forms).exclude(id__in=users_with_a_team)

    # Collect additional information about these participants who aren't on teams yet
    users_without_a_team_details = []

    for person in users_without_a_team:
        email = person.email
       
        signed_agreement_forms = []

        # For each of the available agreement forms for this project, display only latest version completed by the user
        for agreement_form in project.agreement_forms.all():
            signed_agreement_forms.append(SignedAgreementForm.objects.filter(user__email=email, project=project, agreement_form=agreement_form).last())

        users_without_a_team_details.append({
            'email': email,
            # 'user_info': user_info,
            'signed_agreement_forms': signed_agreement_forms,
            'participant': person
        })

    # Simple statistics for display
    all_participants = Participant.objects.filter(data_challenge=project)
    all_submissions = ParticipantSubmission.objects.filter(
        participant__in=all_participants,
        deleted=False
    )
    teams_with_any_submission = all_submissions.select_related('participant').select_related('team')

    institution = project.institution

    return render(request, template_name, {"user": user,
                                           "ssl_setting": settings.SSL_SETTING,
                                           "is_manager": is_manager,
                                           "project": project,
                                           "teams": teams,
                                           "users_without_a_team_details": users_without_a_team_details,
                                           "total_teams": teams.count(),
                                           "total_participants": all_participants.count(),
                                           "total_submissions": all_submissions.count(),
                                           "teams_with_any_submission": teams_with_any_submission.count(),
                                           "institution": institution})

@method_decorator(public_user_auth_and_jwt, name='dispatch')
class DataProjectView(TemplateView):
    """
    Builds and renders screens related to DataProject signup and participation.
    """

    project = None
    template_name = None
    user_jwt = None
    participant = None

    def dispatch(self, request, *args, **kwargs):
        """
        Sets up the instance.
        """

        # Get the project key from the URL.
        project_key = self.kwargs['project_key']

        # If this project does not exist, display a 404 Error.
        try:
            self.project = DataProject.objects.get(project_key=project_key)
        except ObjectDoesNotExist:
            error_message = "The project you searched for does not exist."
            return render(request, '404.html', {'error_message': error_message})

        # Add the user's jwt to the class instance.
        self.user_jwt = request.COOKIES.get("DBMI_JWT", None)

        # Add the participant to the class instance if available.
        if request.user.is_authenticated():
            try:
                self.participant = Participant.objects.get(
                    user=self.request.user,
                    data_challenge=self.project
                )
            except ObjectDoesNotExist:
                pass

        return super(DataProjectView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """
        Dynamically builds the context for rendering the view based on information
        about the user and the DataProject.
        """

        # Get super's context. This is the dictionary of variables for the base template
        # being rendered.
        context = super(DataProjectView, self).get_context_data(**kwargs)

        # Prepare the common context.
        self.get_base_context_data(context)

        # Determine which context is appropriate for this user.
        if not self.request.user.is_authenticated():
            self.get_unregistered_context(context)
        elif not self.is_user_granted_access(context):
            self.get_signup_context(context)
        else:
            self.get_participate_context(context)

        return context

    def get_base_context_data(self, context):
        """
        Include all common context items here, ones that should be available for the base
        template ultimately loaded.
        """

        # Add the project to the context.
        context['project'] = self.project

        # Check if the user is a manager of this DataProject.
        if self.request.user.is_authenticated():
            sciauthz = SciAuthZ(settings.AUTHZ_BASE, self.user_jwt, self.request.user.email)
            context['is_manager'] = sciauthz.user_has_manage_permission(self.project.project_key)
            context['has_view_permission'] = sciauthz.user_has_single_permission(self.project.project_key, "VIEW")

    def get_unregistered_context(self, context):
        """
        Adds to the view's context anything needed for unregistered users to
        be able to learn about this DataProject.
        """

        # Set the template that should be rendered.
        self.template_name = 'shared/login_or_register.html'

        return context

    def get_signup_context(self, context):
        """
        Adds to the view's context anything needed for users to get access to
        this DataProject. The sign up process is broken up into a set of steps
        that affect the user interface. A step contains information needed to
        render a sub template.
        """

        # Initialize the steps list.
        context['steps'] = []

        # Initialize tracking of which step is the current step.
        context['current_step'] = None

        # Verify email step.
        self.step_verify_email(context)

        # SciReg complete profile step.
        self.step_complete_profile(context)

        # Agreement forms step (if needed).
        self.step_sign_agreement_forms(context)

        # Show JWT step (if needed).
        self.step_show_jwt(context)

        # Access request step (if needed).
        self.step_request_access(context)

        # Team setup step (if needed).
        self.step_setup_team(context)

        # Set the template that should be rendered.
        self.template_name = 'project_signup/base.html'

        return context

    def get_participate_context(self, context):
        """
        Adds to the view's context anything needed for participating in a DataProject
        once a user has been granted access to it. The participate screen is comprised of two
        columns and a set of panels in each. A panel contains information needed to
        render a sub template.
        """

        # Initialize as a list the panels that will occupy either side of the participate screen.
        context['left_panels'] = []
        context['right_panels'] = []

        # Add a panel for displaying submitted solutions (if needed).
        self.panel_submissions(context)

        # Add a panel for displaying team members (if needed).
        self.panel_team_members(context)

        # Add a panel for displaying your signed agreement forms (if needed).
        self.panel_signed_agreement_forms(context)

        # Add a panel for a solution submission form (if needed).
        self.panel_submit_solution(context)

        # Add a panel for available downloads.
        self.panel_available_downloads(context)

        # Set the template that should be rendered.
        self.template_name = 'project_participate/base.html'

        return context

    def get_step_status(self, context, step_name, step_complete):
        """
        Returns the status this step should have. If the given step is incomplete and we do not
        already have a current_step in context, then this step is the current step and update
        context to note this. If this step is incomplete but another step has already been deemed
        the current step, then this is a future step.
        """

        if step_complete:
            return 'completed_step'
        elif context['current_step'] is None:
            context['current_step'] = step_name
            return 'current_step'
        else:
            return 'future_step'

    def step_verify_email(self, context):
        """
        Builds the context needed for users to verify their email address. This is
        a required step.
        """

        email_verified = get_user_email_confirmation_status(self.user_jwt)
        step_status = self.get_step_status(context, 'verify_email', email_verified)

        # Describe the step. Include here any variables that the template will need.
        step = {
            'title': 'Verify Your Email',
            'template': 'project_signup/verify_email.html',
            'status': step_status
        }

        context['steps'].append(step)

    def step_complete_profile(self, context):
        """
        Builds the context needed for users to complete their SciReg profile. This is
        a required step.
        """

        scireg_profile_results = get_current_user_profile(self.user_jwt)

        try:
            profile_data = scireg_profile_results["results"][0]

            # Populate our RegistrationForm with SciReg data and check if required fields are completed.
            registration_form = RegistrationForm(profile_data)
            profile_complete = registration_form.is_valid()

            # If the profile is incomplete, use the initial parameter to prevent binding the form data
            # which causes form errors not needed at this time.
            if not profile_complete:
                registration_form = RegistrationForm(initial=profile_data)

        except (KeyError, IndexError):
            profile_complete = False

            # User does not have a registration object in SciReg. Prepare one for them.
            registration_form = RegistrationForm(
                initial={'email': self.request.user.email},
                new_registration=True
            )

        step_status = self.get_step_status(context, 'complete_profile', profile_complete)

        # Describe the step. Include here any variables that the template will need.
        step = {
            'title': 'Complete Your Profile',
            'template': 'project_signup/complete_profile.html',
            'status': step_status,
            'registration_form': registration_form
        }

        context['steps'].append(step)

    def step_sign_agreement_forms(self, context):
        """
        Builds the context needed for users to complete any required agreement forms.
        This is an optional step depending on the DataProject. One step will be added
        for each agreement form required by this DataProject.
        """

        # Do not include this step if this project does not have any agreement forms.
        if self.project.agreement_forms.count() == 0:
            return

        agreement_form_intializer = SignAgreementFormsStepInitializer()

        current_step, steps = agreement_form_intializer.update_context(project=self.project,
                                                                       user=self.request.user,
                                                                       current_step=context["current_step"])

        context["current_step"] = current_step

        for step in steps:
            context['steps'].append(step)

    def step_show_jwt(self, context):
        """
        Builds the context needed for users to see their JWT. This is an optional
        step depending on the DataProject.
        """

        if not self.project.show_jwt:
            return

        # This step is never completed, it is usually the last step.
        status = self.get_step_status(context, 'show_jwt', False)

        # Describe the step. Include here any variables that the template will need.
        step = {
            'title': 'Using Your JWT',
            'template': 'project_signup/show_jwt.html',
            'status': status,
            'user_jwt': self.user_jwt
        }

        context['steps'].append(step)

    def step_request_access(self, context):
        """
        Builds the context needed for users to request access to a DataProject.
        This is an optional step depending on the DataProject.
        """

        # Only display this step if it is a private data set with no agreement forms
        if not (self.project.permission_scheme == "PRIVATE" and self.project.agreement_forms.count() == 0):
            return

        # Check SciAuthZ for any access requests by this user
        sciauthz = SciAuthZ(settings.AUTHZ_BASE, self.user_jwt, self.request.user.email)
        user_access_requests = sciauthz.current_user_access_requests()
        access_requested = self.has_user_requested_access(user_access_requests)

         # This step is never completed, it is usually the last step.
        status = self.get_step_status(context, 'request_access', False)

        # Describe the step. Include here any variables that the template will need.
        step = {
            'title': 'Request Access',
            'template': 'project_signup/request_access.html',
            'status': status,
            'project': self.project,
            'access_requested': access_requested
        }

        context['steps'].append(step)

    def step_setup_team(self, context):
        """
        Builds the context needed for users to create or join a team. This is an
        optional step depending on the DataProject.
        """

        # Do not include this step if this project does not involve teams.
        if not self.project.has_teams:
            return

        team = None
        team_has_pending_members = None

        # If a user has a Participant record, then they have already been associated.
        # with a team.
        if self.participant is not None:
            team = self.participant.team
            team_has_pending_members = Participant.objects.filter(
                team=self.participant.team,
                team_approved=False
            )

        # This step is never completed.
        status = self.get_step_status(context, 'setup_team', False)

        # Describe the step. Include here any variables that the template will need.
        step = {
            'title': 'Join or Create a Team',
            'template': 'project_signup/setup_team.html',
            'status': status,
            'project': self.project,
            'participant': self.participant,
            'team': team,
            'team_has_pending_members': team_has_pending_members
        }

        context['steps'].append(step)

    def panel_submissions(self, context):
        """
        Builds the context needed for a user to view submitted solutions associated
        with them. If this Participant has no team, then they will only see their
        submissions. If this Participant does have a team, they will see the team's
        submissions. This is an optional panel depending on the DataProject.
        """

        # Do not include this panel if this project does not accept submissions.
        if not self.project.accepting_user_submissions:
            return

        # Either get a team or individual's submissions
        if self.participant.team is not None:
            submissions = self.participant.team.get_submissions()
        else:
            submissions = self.participant.get_submissions()

        # Describe the panel. Include here any variables that the template will need.
        panel = {
            'title': 'Solutions Submitted',
            'template': 'project_participate/solutions_submitted.html',
            'submissions': submissions
        }

        # Add the panel to the left column.
        context['left_panels'].append(panel)

    def panel_team_members(self, context):
        """
        Builds the context needed for a user to see who is on their team. This is
        an optional step depending on the DataProject.
        """

        # Do not include this panel if this project does not have teams.
        if not self.project.has_teams and self.participant.team is not None:
            return

        # Describe the panel. Include here any variables that the template will need.
        panel = {
            'title': 'Team Members',
            'template': 'project_participate/team_members.html',
            'team': self.participant.team
        }

        # Add the panel to the left column.
        context['left_panels'].append(panel)

    def panel_signed_agreement_forms(self, context):
        """
        Builds the context needed for a user to see the agreement forms they have
        signed. This is an optional step depending on the DataProject.
        """

        # Do not include this panel if this project does not have agreement forms.
        if self.project.agreement_forms.count() == 0:
            return

        # Get this user's signed agreement forms that have a pending or approved state.
        signed_forms = SignedAgreementForm.objects.filter(
            project=self.project,
            user=self.participant.user,
            status__in=["P", "A"]
        )

        # Describe the panel. Include here any variables that the template will need.
        panel = {
            'title': 'Signed Agreement Forms',
            'template': 'project_participate/signed_agreement_forms.html',
            'signed_forms': signed_forms
        }

        # Add the panel to the left column.
        context['left_panels'].append(panel)

    def panel_submit_solution(self, context):
        """
        Builds the context needed for a user to submit a solution for a data
        challenge. This is an optional step depending on the DataProject.
        """

        # Do not include this panel if this project does not accept solutions.
        if not self.project.accepting_user_submissions:
            return

        # Describe the panel. Include here any variables that the template will need.
        panel = {
            'title': 'Submit Your Solution',
            'template': 'project_participate/submit_solution.html',
            'team': self.participant.team,
            'project': self.project
        }

        # Add the panel to the right column.
        context['right_panels'].append(panel)

    def panel_available_downloads(self, context):
        """
        Builds the context needed for a user to be able to download data sets
        belonging to this DataProject. The downloads panel will always be
        displayed, but there will not always be a download available to the user.
        """

        # Describe the panel. Include here any variables that the template will need.
        panel = {
            'title': 'Available Downloads',
            'template': 'project_participate/available_downloads.html',
            'project': self.project
        }

        # Add the panel to the right column.
        context['right_panels'].append(panel)

    def is_user_granted_access(self, context):
        """
        Determines whether or not a user has met all the necessary requirements to be
        considered having been granted access to participate in this DataProject.
        Returns a boolean.
        """

        # Does user have VIEW or MANAGE permissions?
        if not context['has_view_permission'] and not context['is_manager']:
            return False

        # Additional requirements if a DataProject requires teams.
        if self.project.has_teams:

            # Make sure the user has a Participant record.
            if self.participant is None:
                return False

            # Make sure the team leader has accepted this user onto their team.
            if not self.participant.team_approved:
                return False

            # Make sure the team has been approved by administrators.
            if not self.participant.team.status == 'Active':
                return False

        # If no issues, then the user been granted access.
        return True

    def has_user_requested_access(self, access_requests):
        """
        Determines whether or not a user has already requested access to this DataProject.
        Returns a boolean.
        """

        if access_requests is not None and 'results' in access_requests:
            for access_request in access_requests['results']:
                if access_request['item'] == self.project.project_key:
                    return True
        
        return False