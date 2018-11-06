import json
import logging
from datetime import datetime
import dateutil.parser

from django.conf import settings
from django.contrib.auth import logout

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

from profile.forms import RegistrationForm

from pyauth0jwt.auth0authenticate import logout_redirect
from pyauth0jwt.auth0authenticate import public_user_auth_and_jwt
from pyauth0jwt.auth0authenticate import user_auth_and_jwt
from pyauth0jwt.auth0authenticate import validate_request as validate_jwt

from projects.models import ChallengeTaskSubmission
from projects.models import DataProject
from projects.models import HostedFile
from projects.models import Participant
from projects.models import SignedAgreementForm
from projects.models import PERMISSION_SCHEME_EXTERNALLY_GRANTED

from projects.steps.agreement_forms import SignAgreementFormsStepInitializer
from projects.steps.pending_review import PendingReviewStepInitializer

# Get an instance of a logger
logger = logging.getLogger(__name__)


@user_auth_and_jwt
def signout(request):
    logout(request)
    response = redirect(settings.AUTH0_LOGOUT_URL)
    response.delete_cookie('DBMI_JWT', domain=settings.COOKIE_DOMAIN)
    return response


@user_auth_and_jwt
def signed_agreement_form(request):

    project_key = request.GET['project_key']
    signed_agreement_form_id = request.GET['signed_form_id']

    user_jwt = request.COOKIES.get("DBMI_JWT", None)
    sciauthz = SciAuthZ(settings.AUTHZ_BASE, user_jwt, request.user.email)
    is_manager = sciauthz.user_has_manage_permission(project_key)
    has_manage_permissions = sciauthz.user_has_any_manage_permissions()

    project = get_object_or_404(DataProject, project_key=project_key)
    signed_form = get_object_or_404(SignedAgreementForm, id=signed_agreement_form_id, project=project)

    try:
        participant = Participant.objects.get(data_challenge=project, user=signed_form.user)
    except ObjectDoesNotExist:
        participant = None

    if is_manager or signed_form.user == request.user:
        template_name = "projects/participate/view-signed-agreement-form.html"
        filled_out_signed_form = None

        return render(request, template_name, {"user": request.user,
                                               "ssl_setting": settings.SSL_SETTING,
                                               "has_manage_permissions": has_manage_permissions,
                                               "is_manager": is_manager,
                                               "signed_form": signed_form,
                                               "filled_out_signed_form": filled_out_signed_form,
                                               "participant": participant})
    else:
        return HttpResponse(403)


@public_user_auth_and_jwt
def list_data_projects(request, template_name='projects/list-data-projects.html'):

    all_data_projects = DataProject.objects.filter(is_challenge=False, visible=True)

    data_projects = []
    projects_with_view_permissions = []
    projects_with_access_requests = {}

    has_manage_permissions = False

    if not request.user.is_authenticated():
        user = None
    else:
        user = request.user
        user_jwt = request.COOKIES.get("DBMI_JWT", None)

        # If for some reason they have a session but not JWT, force them to log in again.
        if user_jwt is None or validate_jwt(request) is None:
            return logout_redirect(request)

        sciauthz = SciAuthZ(settings.AUTHZ_BASE, user_jwt, user.email)
        has_manage_permissions = sciauthz.user_has_any_manage_permissions()
        user_permissions = sciauthz.current_user_permissions()

        logger.debug('[HYPATIO][DEBUG] User Permissions: ' + json.dumps(user_permissions))

        if user_permissions is not None and 'results' in user_permissions:
            user_permissions = user_permissions["results"]

            for user_permission in user_permissions:
                if user_permission['permission'] == 'VIEW':
                    projects_with_view_permissions.append(user_permission['item'])

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
                                           "has_manage_permissions": has_manage_permissions,
                                           "account_server_url": settings.ACCOUNT_SERVER_URL,
                                           "profile_server_url": settings.SCIREG_SERVER_URL})


@public_user_auth_and_jwt
def list_data_challenges(request, template_name='projects/list-data-challenges.html'):

    all_data_contests = DataProject.objects.filter(is_challenge=True, visible=True)
    data_contests = []

    has_manage_permissions = False

    if not request.user.is_authenticated():
        user = None
    else:

        user = request.user
        user_jwt = request.COOKIES.get("DBMI_JWT", None)

        # If for some reason they have a session but not JWT, force them to log in again.
        if user_jwt is None or validate_jwt(request) is None:
            return logout_redirect(request)

        if request.user.is_superuser:
            all_data_contests = DataProject.objects.filter(is_challenge=True)

        sciauthz = SciAuthZ(settings.AUTHZ_BASE, user_jwt, user.email)
        has_manage_permissions = sciauthz.user_has_any_manage_permissions()

    # Build the dictionary with all project and permission information needed
    for data_contest in all_data_contests:

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
                                           "has_manage_permissions": has_manage_permissions,
                                           "account_server_url": settings.ACCOUNT_SERVER_URL,
                                           "profile_server_url": settings.SCIREG_SERVER_URL})


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

        # Get super's context. This is the dictionary of variables for the base template being rendered.
        context = super(DataProjectView, self).get_context_data(**kwargs)

        # Prepare the common context.
        self.get_base_context_data(context)

        # Determine which context is appropriate for this user.
        if not self.request.user.is_authenticated() or self.user_jwt is None:
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
            context['has_manage_permissions'] = sciauthz.user_has_manage_permission(self.project.project_key)
            context['has_view_permission'] = sciauthz.user_has_single_permission(self.project.project_key, "VIEW")

    def get_unregistered_context(self, context):
        """
        Adds to the view's context anything needed for unregistered users to
        be able to learn about this DataProject.
        """

        # Set the template that should be rendered.
        self.template_name = 'projects/login-or-register.html'

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

        # Static page that lets user know to wait.
        self.step_pending_review(context)

        # Set the template that should be rendered.
        self.template_name = 'projects/signup/base.html'

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

        # Add a panel for displaying team members (if needed).
        self.panel_team_members(context)

        # Add a panel for displaying your signed agreement forms (if needed).
        self.panel_signed_agreement_forms(context)

        # Add a panel for available downloads.
        self.panel_available_downloads(context)

        # Add a panel for a solution submission form (if needed).
        self.panel_submit_task_solutions(context)

        # Set the template that should be rendered.
        self.template_name = 'projects/participate/base.html'

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
            'template': 'projects/signup/verify-email.html',
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
            profile_data = None
            profile_complete = False

            # User does not have a registration object in SciReg. Prepare one for them.
            registration_form = RegistrationForm(
                initial={'email': self.request.user.email},
                new_registration=True
            )

        step_complete = profile_complete

        if profile_data is not None:
            try:
                profile_last_updated_date = dateutil.parser.parse(profile_data['last_updated']).date()
                days_since_last_profile_update = (datetime.now().date() - profile_last_updated_date).days

                # Mark this step as incomplete if it has been more than two weeks since a user has updated their profile
                if days_since_last_profile_update >= 14:
                    step_complete = False
            except KeyError:
                pass

        step_status = self.get_step_status(context, 'complete_profile', step_complete)

        # Describe the step. Include here any variables that the template will need.
        step = {
            'title': 'Complete Your Profile',
            'template': 'projects/signup/complete-profile.html',
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

        current_step, steps = agreement_form_intializer.update_context(
            project=self.project,
            user=self.request.user,
            current_step=context["current_step"]
        )

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
            'template': 'projects/signup/show-jwt.html',
            'status': status,
            'user_jwt': self.user_jwt
        }

        context['steps'].append(step)

    def step_request_access(self, context):
        """
        Builds the context needed for users to request access to a DataProject.
        This is an optional step depending on the DataProject.
        """

        # -----------------------------------------------------------
        # TODO this is where the new access request logic should live
        # -----------------------------------------------------------

        # Only display this step if it is a private data set with no agreement forms
        if not (self.project.permission_scheme == "PRIVATE" and self.project.agreement_forms.count() == 0):
            return

        # TODO Check for access 
        # access_requested = self.has_user_requested_access(user_access_requests)
        access_requested = False
        
        # This step is never completed, it is usually the last step.
        status = self.get_step_status(context, 'request_access', False)

        # Describe the step. Include here any variables that the template will need.
        step = {
            'title': 'Request Access',
            'template': 'projects/signup/request-access.html',
            'status': status,
            'project': self.project,
            'access_requested': access_requested
        }

        context['steps'].append(step)

    def step_pending_review(self, context):
        """
        Show a static page letting user know their request is pending.
        """

        if self.project.permission_scheme != PERMISSION_SCHEME_EXTERNALLY_GRANTED:
            return

        step = PendingReviewStepInitializer().update_context(project=self.project, context=context)

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
            'template': 'projects/signup/setup-team.html',
            'status': status,
            'project': self.project,
            'participant': self.participant,
            'team': team,
            'team_has_pending_members': team_has_pending_members
        }

        context['steps'].append(step)

    def panel_team_members(self, context):
        """
        Builds the context needed for a user to see who is on their team. This is
        an optional step depending on the DataProject.
        """

        # Do not include this panel if this project does not have teams.
        if not self.project.has_teams or (self.participant is not None and self.participant.team is not None):
            return

        # Describe the panel. Include here any variables that the template will need.
        panel = {
            'title': 'Team Members',
            'template': 'projects/participate/team-members.html',
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
            user=self.request.user,
            status__in=["P", "A"]
        )

        # Describe the panel. Include here any variables that the template will need.
        panel = {
            'title': 'Signed Agreement Forms',
            'template': 'projects/participate/signed-agreement-forms.html',
            'signed_forms': signed_forms
        }

        # Add the panel to the left column.
        context['left_panels'].append(panel)

    def panel_submit_task_solutions(self, context):
        """
        Builds the context needed for a user to submit solutions for a data
        challenge's task. A data challenge may require more than one solution. This
        is an optional step depending on the DataProject.
        """

        tasks = self.project.challengetask_set.all()

        # Do not include this panel if this project does not have any tasks        
        if tasks.count() == 0:
            return

        task_details = []

        for task in tasks:

            # Get the submissions for this task already submitted by the team.
            submissions = ChallengeTaskSubmission.objects.filter(
                challenge_task=task,
                participant__in=self.participant.team.participant_set.all(),
                deleted=False
            )

            total_submissions = submissions.count()

            task_context = {
                'task': task,
                'submissions': submissions,
                'total_submissions': total_submissions,
                'submissions_left': task.max_submissions - total_submissions
            }

            task_details.append(task_context)

        # Describe the panel. Include here any variables that the template will need.
        panel = {
            'title': 'Tasks to Complete',
            'template': 'projects/participate/complete-tasks.html',
            'team': self.participant.team,
            'project': self.project,
            'task_details': task_details
        }

        # Add the panel to the right column.
        context['right_panels'].append(panel)

    def panel_available_downloads(self, context):
        """
        Builds the context needed for a user to be able to download data sets
        belonging to this DataProject. Will a panel for every HostedFileSet and another
        for any files not belonging to a set.
        """

        # Create a panel for each HostedFileSet
        for file_set in self.project.hostedfileset_set.all():

            # Describe the panel. Include here any variables that the template will need.
            panel = {
                'title': file_set.title + ' Downloads',
                'template': 'projects/participate/available-downloads.html',
                'project': self.project,
                'files': file_set.hostedfile_set.all()
            }

            # Add the panel to the right column.
            context['right_panels'].append(panel)

        # Add another panel for files that do not belong to a HostedFileSet
        files_without_a_set = HostedFile.objects.filter(
            project=self.project,
            hostedfileset=None
        )

        if files_without_a_set.count() > 0:

            # Describe the panel. Include here any variables that the template will need.
            panel = {
                'title': 'Available Downloads',
                'template': 'projects/participate/available-downloads.html',
                'project': self.project,
                'files': files_without_a_set
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
        if not context['has_view_permission'] and not context['has_manage_permissions']:
            return False

        # If the permission is managed outside this project, return false.
        if self.project.permission_scheme == PERMISSION_SCHEME_EXTERNALLY_GRANTED:
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

        # TODO UPDATE THIS FOR NEW METHOD OF REQUESTING ACCESS...
        # ...

        return False
