import logging
from datetime import datetime
import dateutil.parser
from furl import furl

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import F
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from django.shortcuts import redirect

from hypatio.sciauthz_services import SciAuthZ
from hypatio.dbmiauthz_services import DBMIAuthz
from hypatio.scireg_services import get_current_user_profile
from hypatio.scireg_services import get_user_email_confirmation_status
from profile.forms import RegistrationForm
from hypatio.auth0authenticate import public_user_auth_and_jwt
from hypatio.auth0authenticate import user_auth_and_jwt
from projects.models import AGREEMENT_FORM_TYPE_EXTERNAL_LINK, TEAM_ACTIVE, TEAM_READY
from projects.models import AGREEMENT_FORM_TYPE_STATIC
from projects.models import AGREEMENT_FORM_TYPE_MODEL
from projects.models import AGREEMENT_FORM_TYPE_FILE
from projects.models import AGREEMENT_FORM_TYPE_BLANK
from projects.models import ChallengeTaskSubmission
from projects.models import DataProject
from projects.models import HostedFile
from projects.models import Participant
from projects.models import AgreementForm
from projects.models import SignedAgreementForm
from projects.models import Group
from projects.models import InstitutionalOfficial
from projects.models import DataUseReportRequest
from projects.models import SIGNED_FORM_APPROVED
from projects.panels import SIGNUP_STEP_COMPLETED_STATUS
from projects.panels import SIGNUP_STEP_CURRENT_STATUS
from projects.panels import SIGNUP_STEP_FUTURE_STATUS
from projects.panels import SIGNUP_STEP_PERMANENT_STATUS
from projects.panels import DataProjectInformationalPanel
from projects.panels import DataProjectSignupPanel
from projects.panels import DataProjectActionablePanel
from projects.panels import DataProjectSharedTeamsPanel
from projects.panels import DataProjectInstitutionalOfficialPanel

# Get an instance of a logger
logger = logging.getLogger(__name__)


@user_auth_and_jwt
def data_use_report(request, request_id):

    # Get the original request
    data_use_report_request = get_object_or_404(DataUseReportRequest, id=request_id)

    user_jwt = request.COOKIES.get("DBMI_JWT", None)
    sciauthz = SciAuthZ(user_jwt, request.user.email)
    is_manager = sciauthz.user_has_manage_permission(data_use_report_request.data_project.project_key)
    participant = data_use_report_request.participant

    template_name = "projects/participate/data-use-report.html"

    return render(request, template_name, {
        "user": request.user,
        "is_manager": is_manager,
        "agreement_form": data_use_report_request.data_project.data_use_report_agreement_form,
        "participant": participant,
        "project": participant.project,
        "form_context": {},
    })


@user_auth_and_jwt
def signed_agreement_form(request):

    project_key = request.GET['project_key']
    signed_agreement_form_id = request.GET['signed_form_id']

    user_jwt = request.COOKIES.get("DBMI_JWT", None)
    sciauthz = SciAuthZ(user_jwt, request.user.email)
    is_manager = sciauthz.user_has_manage_permission(project_key)

    project = get_object_or_404(DataProject, project_key=project_key)
    signed_form = get_object_or_404(SignedAgreementForm, id=signed_agreement_form_id, project=project)

    try:
        participant = Participant.objects.get(project=project, user=signed_form.user)
    except ObjectDoesNotExist:
        participant = None

    # Get fields, if applicable. It sucks that these are hard-coded but until we
    # find a better solution and have more time, this is it.
    signed_agreement_form_fields = {}

    if is_manager or signed_form.user == request.user:
        template_name = "projects/participate/view-signed-agreement-form.html"
        filled_out_signed_form = None

        return render(request, template_name, {"user": request.user,
                                               "ssl_setting": settings.SSL_SETTING,
                                               "is_manager": is_manager,
                                               "signed_form": signed_form,
                                               "filled_out_signed_form": filled_out_signed_form,
                                               "signed_agreement_form_fields": signed_agreement_form_fields,
                                               "participant": participant})
    else:
        return HttpResponse(403)


@public_user_auth_and_jwt
def list_data_projects(request, template_name='projects/list-data-projects.html'):
    """
    Displays all visible data projects.
    """

    context = {}
    context['projects'] = DataProject.objects.filter(is_dataset=True, visible=True).order_by(F('order').asc(nulls_last=True))

    return render(request, template_name, context=context)


@public_user_auth_and_jwt
def list_data_challenges(request, template_name='projects/list-data-challenges.html'):
    """
    Displays all visible data challenges.
    """

    context = {}
    context['projects'] = DataProject.objects.filter(is_challenge=True, visible=True).order_by(F('order').asc(nulls_last=True))

    return render(request, template_name, context=context)


@public_user_auth_and_jwt
def list_software_projects(request, template_name='projects/list-software-projects.html'):
    """
    Displays all visible software projects.
    """

    context = {}
    context['projects'] = DataProject.objects.filter(is_software=True, visible=True).order_by(F('order').asc(nulls_last=True))

    return render(request, template_name, context=context)


@method_decorator(public_user_auth_and_jwt, name='dispatch')
class GroupView(TemplateView):
    """
    Builds and renders screens related to Groups.
    """

    group = None
    template_name = 'projects/group.html'

    def dispatch(self, request, *args, **kwargs):
        """
        Sets up the instance.
        """

        # Get the project key from the URL.
        group_key = self.kwargs['group_key']

        # If this project does not exist, display a 404 Error.
        try:
            self.group = Group.objects.get(key=group_key)
        except ObjectDoesNotExist:
            error_message = "The group you searched for does not exist."
            return render(request, '404.html', {'error_message': error_message})

        return super(GroupView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """
        Dynamically builds the context for rendering the view based on information
        about the user and the Group.
        """
        # Get super's context. This is the dictionary of variables for the base template being rendered.
        context = super(GroupView, self).get_context_data(**kwargs)

        # Add the project to the context.
        context['group'] = self.group
        context['projects'] = DataProject.objects.filter(group=self.group, visible=True).order_by(F('order').asc(nulls_last=True))

        return context


@method_decorator(public_user_auth_and_jwt, name='dispatch')
class DataProjectView(TemplateView):
    """
    Builds and renders screens related to DataProject signup and participation.
    """

    project = None
    user_jwt = None
    participant = None
    current_step = None
    email_verified = None
    template_name = 'projects/project.html'

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
        if request.user.is_authenticated:
            try:
                self.participant = Participant.objects.get(
                    user=self.request.user,
                    project=self.project
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

        # Add the project to the context.
        context['project'] = self.project

        # Initialize lists to store the different groupings of panels that will be displayed.
        context['informational_panels'] = []
        context['setup_panels'] = []
        context['actionable_panels'] = []

        # Add a few variables needed for the UI.
        context['SIGNUP_STEP_COMPLETED_STATUS'] = SIGNUP_STEP_COMPLETED_STATUS
        context['SIGNUP_STEP_CURRENT_STATUS'] = SIGNUP_STEP_CURRENT_STATUS
        context['SIGNUP_STEP_FUTURE_STATUS'] = SIGNUP_STEP_FUTURE_STATUS
        context['SIGNUP_STEP_PERMANENT_STATUS'] = SIGNUP_STEP_PERMANENT_STATUS

        # If this project is informational only, just show them the description without requiring an account.
        if self.project.informational_only:
            self.get_informational_only_context(context)
            return context

        # Otherwise, users who are not logged in should be prompted to first before proceeding further.
        if not self.request.user.is_authenticated or self.user_jwt is None:
            self.get_unregistered_context(context)
            return context

        # Check the users current permissions on this project.
        if self.request.user.is_authenticated:
            context['has_manage_permissions'] = DBMIAuthz.user_has_manage_permission(
                request=self.request, project_key=self.project.project_key
            )
            # If user has MANAGE, VIEW is implicit
            context['has_view_permission'] = context['has_manage_permissions'] or \
                                             DBMIAuthz.user_has_view_permission(
                                                 request=self.request, project_key=self.project.project_key
                                             )

        # Require users to verify their email no matter what before they access a project.
        self.email_verified = get_user_email_confirmation_status(self.user_jwt)
        if not self.email_verified:
            self.get_signup_context(context)
            return context

        # If a user is already granted access to a project, only show them the participation panels.
        if self.is_user_granted_access(context):
            self.get_participate_context(context)
            return context

        # If a user is a manager of the project, show them only specific panels.
        if context['has_manage_permissions']:
            self.get_manager_context(context)
            return context

        # If registration is closed, do not allow them to go further.
        if not self.project.registration_open:
            self.get_project_registration_closed_context(context)
            return context

        # If a project does not require any authorization, display signup and participation steps all at once.
        if not self.project.requires_authorization:
            self.get_signup_context(context)
            self.get_participate_context(context)
            return context

        # Otherwise, prompt the user to sign up.
        self.get_signup_context(context)

        return context

    def get_informational_only_context(self, context):
        """
        Adds to the view's context anything needed to display a project's description
        with no further actions or features.
        """

        # Set the template that should be rendered.
        self.template_name = 'projects/description-only.html'

        return context

    def get_unregistered_context(self, context):
        """
        Adds to the view's context anything needed for unregistered users to
        be able to learn about this DataProject.
        """

        # Set the template that should be rendered.
        self.template_name = 'projects/login-or-register.html'

        return context

    def get_project_registration_closed_context(self, context):
        """
        Adds to the view's context anything needed to show users without access
        that the project is closed to further registrations.
        """

        # Set the template that should be rendered.
        self.template_name = 'projects/registration-closed.html'

        return context

    def get_signup_context(self, context):
        """
        Adds to the view's context anything needed for users to do to get access to
        this DataProject. The sign up process is broken up into a set of steps
        that affect the user interface. A step contains information needed to
        render a sub template.
        """

        # Verify email step.
        self.setup_panel_verify_email(context)

        # SciReg complete profile step.
        self.setup_panel_complete_profile(context)

        # Check if this project uses shared teams
        if self.project.teams_source and not Participant.objects.filter(user=self.request.user, team__data_project=self.project, team__status=TEAM_READY).exists():

            # Show panel
            self.setup_panel_shared_teams(context)

        else:

            # Set institutional context
            self.get_institutional_context(context)

            # Agreement forms step (if needed).
            self.setup_panel_sign_agreement_forms(context)

            # Access request step (if needed).
            self.setup_panel_request_access(context)

            # Show JWT step (if needed).
            self.setup_panel_show_jwt(context)

            # Team setup step (if needed).
            self.setup_panel_team(context)

            # TODO commented out until this is ready.
            # Static page that lets user know to wait.
            # self.step_pending_review(context)
        return context

    def get_institutional_context(self, context):
        """
        Prepares context for institional signer status, if applicable
        """
        # Check if this project/agreement form accepts institutional signers
        if self.project.institutional_signers:
            try:
                # Check for one
                context["institutional_official"] = InstitutionalOfficial.objects.get(
                    project=self.project,
                    member_emails__contains=self.request.user.email,
                )
            except ObjectDoesNotExist:
                pass

    def get_participate_context(self, context):
        """
        Adds to the view's context anything needed for participating in a DataProject
        once a user has been granted access to it.
        """

        # Add a panel for displaying team members (if needed).
        self.panel_team_members(context)

        # Add a panel for displaying your signed agreement forms (if needed).
        self.panel_signed_agreement_forms(context)

        # Add a panel for projects
        self.panel_available_projects(context)

        # Add a panel for available downloads.
        self.panel_available_downloads(context)

        # Add a panel for a solution submission form (if needed).
        self.panel_submit_task_solutions(context)

        # Add panel for institutional officials
        self.panel_institutional_official(context)

        return context

    def get_manager_context(self, context):
        """
        Adds to the view's context anything that project managers should see who are not
        otherwise participating in the project.
        """

        # Add a panel for projects
        self.panel_available_projects(context)

        # Add a panel for available downloads.
        self.panel_available_downloads(context)

        # Add a panel for a solution submission form (if needed).
        self.panel_submit_task_solutions(context)

        return context

    def get_step_status(self, step_name, step_complete, is_permanent=False):
        """
        Returns the status this step should have. If the given step is incomplete and we do not
        already have a current_step, then this step is the current step and update
        context to note this. If this step is incomplete but another step has already been deemed
        the current step, then this is a future step.
        """

        if step_complete:

            if is_permanent:
                return SIGNUP_STEP_PERMANENT_STATUS

            logger.debug(f"{self.project.project_key}/{step_name}: Completed step")
            return SIGNUP_STEP_COMPLETED_STATUS

        if self.current_step is None:
            self.current_step = step_name
            logger.debug(f"{self.project.project_key}/{step_name}: Current step")
            return SIGNUP_STEP_CURRENT_STATUS

        logger.debug(f"{self.project.project_key}/{step_name}: Future step, {self.current_step}: Current step")
        return SIGNUP_STEP_FUTURE_STATUS

    def setup_panel_verify_email(self, context):
        """
        Builds the context needed for users to verify their email address. This is
        a required step.
        """

        step_status = self.get_step_status('verify_email', self.email_verified)

        panel = DataProjectSignupPanel(
            title='Verify Your Email',
            bootstrap_color='default',
            template='projects/signup/verify-email.html',
            status=step_status
        )

        context['setup_panels'].append(panel)

    def setup_panel_complete_profile(self, context):
        """
        Builds the context needed for users to complete or update their SciReg profile.
        This is a required step.
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

                # Log errors
                logger.debug(f"{self.project.project_key}/{self.request.user.email}: Registration form errors: {registration_form.errors.as_json()}")

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

        step_status = self.get_step_status('complete_profile', step_complete)

        panel = DataProjectSignupPanel(
            title='Complete Your Profile',
            bootstrap_color='default',
            template='projects/signup/complete-profile.html',
            status=step_status,
            additional_context={'registration_form': registration_form}
        )

        context['setup_panels'].append(panel)

    def setup_panel_shared_teams(self, context):
        """
        Builds the context needed for users to be informed of a team sharing setup. This requires
        users to register with another project before requesting access to this one.
        """
        step_status = self.get_step_status('setup_shared_team', False)

        panel = DataProjectSharedTeamsPanel(
            title='Data Project Teams',
            bootstrap_color='default',
            template='projects/signup/shared-teams.html',
            status=step_status,
            additional_context={'project': self.project}
        )

        context['setup_panels'].append(panel)

    def setup_panel_sign_agreement_forms(self, context):
        """
        Builds the context needed for users to complete any required agreement forms.
        This is an optional step depending on the DataProject. One step will be added
        for each agreement form required by this DataProject.
        """

        # Do not include this step if this project does not have any agreement forms.
        if self.project.agreement_forms.count() == 0:
            return

        agreement_forms = self.project.agreement_forms.order_by('order', '-name')

        # Each form will be a separate step.
        for agreement_form in agreement_forms:
            logger.debug(f"{self.project.project_key}/{agreement_form.short_name}: Checking panel signed agreement form")

            # Only include Pending or Approved forms when searching.
            signed_forms = SignedAgreementForm.objects.filter(
                user=self.request.user,
                project=self.project,
                agreement_form=agreement_form,
                status__in=["P", "A"]
            )
            logger.debug(f"{self.project.project_key}/{agreement_form.short_name}: Found {len(signed_forms)} signed P/A forms")

            # If this project accepts agreement forms from other projects, check those too
            if not signed_forms and self.project.shares_agreement_forms:

                # Fetch without a specific project
                signed_forms = SignedAgreementForm.objects.filter(
                    user=self.request.user,
                    agreement_form=agreement_form,
                    status__in=["P", "A"]
                )
                logger.debug(f"{self.project.project_key}/{agreement_form.short_name}: Found {len(signed_forms)} shared signed P/A forms")

            # If the form has already been signed, then the step should be complete.
            step_complete = signed_forms.count() > 0
            logger.debug(f"{self.project.project_key}/{agreement_form.short_name}: Step is completed: {step_complete}")

            # If the form lives externally, then the step will be marked as permanent because we cannot tell if it was completed.
            permanent_step = agreement_form.type == AGREEMENT_FORM_TYPE_EXTERNAL_LINK

            step_status = self.get_step_status(agreement_form.short_name, step_complete, permanent_step)
            logger.debug(f"{self.project.project_key}/{agreement_form.short_name}: Step status: {step_status}")

            title = 'Form: {name}'.format(name=agreement_form.name)

            if not agreement_form.type or agreement_form.type == AGREEMENT_FORM_TYPE_STATIC or agreement_form.type == AGREEMENT_FORM_TYPE_MODEL:
                template = 'projects/signup/sign-agreement-form.html'
            elif agreement_form.type == AGREEMENT_FORM_TYPE_FILE:
                template = 'projects/signup/upload-agreement-form.html'
            elif agreement_form.type == AGREEMENT_FORM_TYPE_EXTERNAL_LINK:
                template = 'projects/signup/sign-external-agreement-form.html'
            elif agreement_form.type == AGREEMENT_FORM_TYPE_BLANK:
                template = 'projects/signup/blank-agreement-form.html'
            else:
                raise Exception("Agreement form type Not implemented")

            # Check if this agreement form has a specified form class
            form = None
            if agreement_form.form_class:
                try:
                    # Initialize an instance of the form
                    form = agreement_form.form(self.request, self.project)

                except Exception as e:
                    logger.exception(f"Agreement form error: {e}", exc_info=True)

            # Get additional context if required by specific AgreementForm
            additional_context = self.get_agreement_form_additional_context(agreement_form, context)

            # Update it with general context
            additional_context.update({
                "agreement_form": agreement_form,
                "form": form,
                "institutional_official": context.get("institutional_official"),
            })

            panel = DataProjectSignupPanel(
                title=title,
                bootstrap_color='default',
                template=template,
                status=step_status,
                additional_context=additional_context,
            )

            context['setup_panels'].append(panel)

    def setup_panel_show_jwt(self, context):
        """
        Builds the context needed for users to see their JWT. This is an optional
        step depending on the DataProject.
        """

        if not self.project.show_jwt:
            return

        # TODO never completed?
        # This step is never completed, it is usually the last step.
        step_status = self.get_step_status('show_jwt', False)

        panel = DataProjectSignupPanel(
            title='Using Your JWT',
            bootstrap_color='default',
            template='projects/signup/show-jwt.html',
            status=step_status,
            additional_context={'user_jwt': self.user_jwt}
        )

        context['setup_panels'].append(panel)

    def setup_panel_request_access(self, context):
        """
        Builds the context needed for users to request access to a DataProject.
        This is an optional step depending on the DataProject.
        """

        # Only display this step if it is a private data set and the project does not use teams.
        if not self.project.requires_authorization or self.project.has_teams:
            return

        # This step is never completed, it is usually the last step.
        step_status = self.get_step_status('request_access', False)

        # If the user does not have a participant record, they have not yet requested access.
        requested_access = self.participant is not None

        panel = DataProjectSignupPanel(
            title='Request Access',
            bootstrap_color='default',
            template='projects/signup/request-access.html',
            status=step_status,
            additional_context={
                'requested_access': requested_access,
                'automatic_authorization': self.project.automatic_authorization,
            }
        )

        context['setup_panels'].append(panel)

    def setup_panel_team(self, context):
        """
        Builds the context needed for users to create or join a team. This is an
        optional step depending on the DataProject.
        """

        # Do not include this step if this project does not involve teams.
        if not self.project.has_teams:
            return

        team = None
        team_has_pending_members = None

        # If a user has a Participant record, then they have already been associated with a team.
        if self.participant is not None:
            team = self.participant.team
            team_has_pending_members = Participant.objects.filter(
                team=self.participant.team,
                team_approved=False
            )

        # This step is never completed.
        step_status = self.get_step_status('setup_team', False)

        panel = DataProjectSignupPanel(
            title='Join or Create a Team',
            bootstrap_color='default',
            template='projects/signup/setup-team.html',
            status=step_status,
            additional_context={
                'participant': self.participant,
                'team': team,
                'team_has_pending_members': team_has_pending_members
            }
        )

        context['setup_panels'].append(panel)

    def panel_team_members(self, context):
        """
        Builds the context needed for a user to see who is on their team. This is
        an optional step depending on the DataProject.
        """

        # Do not include this panel if this project does not have teams
        if not self.project.has_teams:
            return

        additional_context = {}
        additional_context['team'] = self.participant.team

        panel = DataProjectInformationalPanel(
            title='Team Members',
            bootstrap_color='default',
            template='projects/participate/team-members.html',
            additional_context=additional_context
        )

        context['informational_panels'].append(panel)

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

        panel = DataProjectInformationalPanel(
            title='Signed Agreement Forms',
            bootstrap_color='default',
            template='projects/participate/signed-agreement-forms.html',
            additional_context={'signed_forms': signed_forms}
        )

        context['informational_panels'].append(panel)

    def panel_available_projects(self, context):
        """
        Builds the context needed for a user to be able to view any
        related DataProjects to this one via team sharing.
        """
        # Check if we should list sub-projects
        sub_projects = DataProject.objects.filter(teams_source=self.project)
        if not sub_projects:
            return

        # List them
        panel = DataProjectActionablePanel(
            title='Tasks',
            bootstrap_color='default',
            template='projects/participate/sub-project-listing.html',
            additional_context={'sub_projects': sub_projects,}
        )

        context['actionable_panels'].append(panel)

    def panel_available_downloads(self, context):
        """
        Builds the context needed for a user to be able to download data sets
        belonging to this DataProject. Will a panel for every HostedFileSet and another
        for any files not belonging to a set.
        """

        # Create a panel for each HostedFileSet
        for file_set in self.project.hostedfileset_set.all().order_by(F('order').asc(nulls_last=True)):

            files = file_set.hostedfile_set.all().order_by(F('order').asc(nulls_last=True))

            panel = DataProjectActionablePanel(
                title=file_set.title + ' Downloads',
                bootstrap_color='default',
                template='projects/participate/available-downloads.html',
                additional_context={'files': files}
            )

            context['actionable_panels'].append(panel)

        # Add another panel for files that do not belong to a HostedFileSet
        files_without_a_set = HostedFile.objects.filter(
            project=self.project,
            hostedfileset=None,
            enabled=True
        )

        if files_without_a_set.count() > 0:

            files_without_a_set_sorted = files_without_a_set.order_by(F('order').asc(nulls_last=True))

            panel = DataProjectActionablePanel(
                title='Available Downloads',
                bootstrap_color='default',
                template='projects/participate/available-downloads.html',
                additional_context={'files': files_without_a_set_sorted}
            )

            context['actionable_panels'].append(panel)

        # If no files at all, display an appropriate message.
        if not self.project.hostedfile_set.all().exists():

            panel = DataProjectActionablePanel(
                title='Downloads',
                bootstrap_color='default',
                template='projects/participate/available-downloads.html',
                additional_context={'files': None}
            )

            context['actionable_panels'].append(panel)

    def panel_institutional_official(self, context):
        """
        Builds the context needed for the institutional official to manage
        the members that they provide signing authority for.
        """
        try:
            # Check for an institutional official linked to this user
            official = InstitutionalOfficial.objects.get(user=self.request.user)

            # Add a panel
            panel = DataProjectInstitutionalOfficialPanel(
                title='Institutional Official',
                bootstrap_color='default',
                template='projects/participate/institutional-official.html',
                additional_context={
                    "official": official,
                }
            )

            context['actionable_panels'].append(panel)
        except ObjectDoesNotExist:
            pass

    def panel_submit_task_solutions(self, context):
        """
        Builds the context needed for a user to submit solutions for a data
        challenge's task. A data challenge may require more than one solution. This
        is an optional step depending on the DataProject.
        """

        tasks = self.project.challengetask_set.all()

        # Do not include this panel if this project does not have any tasks.
        if tasks.count() == 0:
            return

        # If the user does not yet have a participant record, create one:
        if self.participant is None:
            self.participant = Participant(user=self.request.user, project=self.project)
            self.participant.save()

        additional_context = {}
        task_details = []

        for task in tasks:

            if self.participant.team is not None:

                # Get the submissions for this task already submitted by the team or individual.
                submissions = ChallengeTaskSubmission.objects.filter(
                    challenge_task=task,
                    participant__in=self.participant.team.participant_set.all(),
                    deleted=False
                )

            else:

                # Get the submissions for this task already submitted by the individual.
                submissions = ChallengeTaskSubmission.objects.filter(
                    challenge_task=task,
                    participant=self.participant,
                    deleted=False
                )

            total_submissions = submissions.count()

            if task.max_submissions is None:
                submissions_left = None
            else:
                submissions_left = task.max_submissions - total_submissions

            task_context = {
                'task': task,
                'submissions': submissions,
                'total_submissions': total_submissions,
                'submissions_left': submissions_left
            }

            task_details.append(task_context)

        additional_context['tasks'] = task_details

        panel = DataProjectActionablePanel(
            title='Tasks to Complete',
            bootstrap_color='default',
            template='projects/participate/complete-tasks.html',
            additional_context=additional_context
        )

        context['actionable_panels'].append(panel)

    def is_user_granted_access(self, context):
        """
        Determines whether or not a user has met all the necessary requirements to be
        considered having been granted access to participate in this DataProject.
        Returns a boolean.
        """

        # Does user not have VIEW permissions?
        if not context['has_view_permission']:
            return False

        # Additional requirements if a DataProject requires teams.
        if self.project.has_teams:

            # Make sure the user has a Participant record.
            if self.participant is None:
                return False

            # Make sure the user is on a team.
            if self.participant.team is None:
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

    def get_agreement_form_additional_context(self, agreement_form, context):
        """
        Adds to the AgreementForm's context
        """
        # Default to empty object
        additional_context = {}

        # Set the method name using the project key.
        method_name = agreement_form.short_name.replace("-", "_") + '_additional_context'

        # Check if this method is implemented.
        if hasattr(self, method_name):
            # Call the method dynamically.
            method = getattr(self, method_name)
            if callable(method):
                logger.debug(f"Calling {method_name}()")
                additional_context = method(agreement_form, context)
            else:
                logger.warning(f"{method_name} is not callable.")
        else:
            logger.warning(f"{method_name} does not exist.")

        return additional_context

    def maida_question_additional_context(self, agreement_form, context):
        """
        Adds to the view's context anything needed for users to sign up for the MAIDA upload project.
        """
        # Set new object for additional context
        additional_context = {}

        # Set the the questionnaire URL.
        questionnaire_url = furl(settings.MAIDA_UPLOAD_QUESTIONNAIRE_URL)
        questionnaire_url.args['email'] = self.request.user.email
        questionnaire_url.args['project_key'] = self.project.project_key
        questionnaire_url.args['agreement_form_id'] = agreement_form.id
        additional_context['maida_questionnaire_url'] = questionnaire_url.url

        return additional_context


@public_user_auth_and_jwt
def qualtrics(request):
    """
    An HTTP GET endpoint that handles Qualtrics redirects when a user finishes a survey
    """
    logger.debug(f"[qualtrics]: GET -> {request.GET}")

    # Get the AgreementForm ID
    agreement_form_id = request.GET.get("agreement_form_id", None)
    if not agreement_form_id:
        return HttpResponse("Error: 'agreement_form_id' is a required parameter.", status=400)

    # Get the survey ID
    survey_id = request.GET.get("survey_id", None)
    if not survey_id:
        return HttpResponse("Error: 'survey_id' is a required parameter.", status=400)

    # Get the project key
    project_key = request.GET.get("project_key", None)
    if not project_key:
        return HttpResponse("Error: 'project_key' is a required parameter.", status=400)

    # Get the project key
    response_id = request.GET.get("response_id", None)
    if not project_key:
        return HttpResponse("Error: 'response_id' is a required parameter.", status=400)

    # Get the project
    project = get_object_or_404(DataProject, project_key=project_key)
    agreement_form = get_object_or_404(AgreementForm, id=agreement_form_id)

    # Create a SignedAgreementForm object
    SignedAgreementForm.objects.create(
        user=request.user,
        agreement_form=agreement_form,
        project=project,
        date_signed=datetime.now(),
        fields={
            "survey_id": survey_id,
            "response_id": response_id,
        },
        status=SIGNED_FORM_APPROVED,
    )

    return redirect(f"/projects/{project_key}/")  # Redirect to the project page
