import json
import logging
import sys
import requests
from datetime import datetime

from django.conf import settings
from django.contrib.auth import logout
from django.contrib.auth.models import User
from django.db.models import Count
from django.shortcuts import render
from django.shortcuts import redirect
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

from pyauth0jwt.auth0authenticate import user_auth_and_jwt
from pyauth0jwt.auth0authenticate import public_user_auth_and_jwt
from pyauth0jwt.auth0authenticate import validate_request as validate_jwt
from pyauth0jwt.auth0authenticate import logout_redirect

from .models import DataProject
from .models import Participant
from .models import Team
from .models import AgreementForm
from .models import SignedAgreementForm
from .models import HostedFile
from .models import HostedFileDownload
from .models import TeamComment
from .models import ParticipantSubmission

from profile.views import get_task_context_data
from profile.forms import RegistrationForm

from django.http import HttpResponse
from django.core.exceptions import ObjectDoesNotExist

from hypatio.sciauthz_services import SciAuthZ
from hypatio.scireg_services import get_user_profile
from hypatio.scireg_services import get_current_user_profile
from hypatio.scireg_services import get_user_email_confirmation_status

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
def signed_agreement_form(request, template_name='signed_agreement_form.html'):

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

        # TODO: commented out because these are too many api calls to make
        # Make a request to SciReg for a specific person's user information
        # user_info_json = get_user_profile(user_jwt, email, project_key)

        # if user_info_json['count'] != 0:
        #     user_info = user_info_json["results"][0]
        # else:
        #     user_info = None
        
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
    total_teams = teams.count()
    total_participants = Participant.objects.filter(data_challenge=project).count()
    countries_represented = '?' # TODO
    total_submissions = 0 # TODO
    teams_with_any_submission = 0 # TODO

    institution = project.institution

    return render(request, template_name, {"user": user,
                                           "ssl_setting": settings.SSL_SETTING,
                                           "is_manager": is_manager,
                                           "project": project,
                                           "teams": teams,
                                           "users_without_a_team_details": users_without_a_team_details,
                                           "total_teams": total_teams,
                                           "total_participants": total_participants,
                                           "countries_represented": countries_represented,
                                           "total_submissions": total_submissions,
                                           "teams_with_any_submission": teams_with_any_submission,
                                           "institution": institution})

@user_auth_and_jwt
def grant_access_with_view_permissions(request):

    user = request.user
    user_jwt = request.COOKIES.get("DBMI_JWT", None)
    jwt_headers = {"Authorization": "JWT " + user_jwt, 'Content-Type': 'application/json'}

    project = request.POST['project']
    person_email = request.POST['user_email']
    authorization_request_id = request.POST['authorization_request_id']

    current_time = datetime.strftime(datetime.now(), "%Y-%m-%dT%H:%M:%S")

    logger.debug('[HYPATIO][DEBUG] Granting authorization request ' + authorization_request_id + ' and view permissions to ' + person_email + ' for project ' + project + '.')

    sciauthz = SciAuthZ(settings.AUTHZ_BASE, user_jwt, user.email)
    is_manager = sciauthz.user_has_manage_permission(project)

    if not is_manager:
        logger.debug('[HYPATIO][DEBUG] User ' + user.email + ' does not have MANAGE permissions for item ' + project + '.')
        return HttpResponse(403)

    # Grab the full authorization request object from SciAuthZ to have all fields necessary for serialization
    authorization_request_url = settings.AUTHORIZATION_REQUEST_URL + "?id=" + authorization_request_id
    authorization_request = requests.get(authorization_request_url, headers=jwt_headers, verify=settings.VERIFY_REQUESTS).json()

    if authorization_request is not None and 'results' in authorization_request:
        authorization_request_data = authorization_request['results'][0]
        logger.debug('[HYPATIO][DEBUG] authorization_request_data ' + json.dumps(authorization_request_data))
    else:
        # This authorization request should have been found
        return HttpResponse(404)

    # Update the granted flag in the authorization request
    authorization_request_data['request_granted'] = True
    authorization_request_data['date_request_granted'] = current_time

    authorization_request_url = settings.AUTHORIZATION_REQUEST_GRANT_URL + authorization_request_id + '/'
    requests.put(authorization_request_url, headers=jwt_headers, data=json.dumps(authorization_request_data), verify=settings.VERIFY_REQUESTS)

    user_permission = {"user": person_email,
                       "item": project,
                       "permission": "VIEW",
                       "date_updated": current_time}

    # Add a VIEW permission to the user
    permissions_url = settings.USER_PERMISSIONS_URL
    user_permissions = requests.post(permissions_url, headers=jwt_headers, data=json.dumps(user_permission), verify=settings.VERIFY_REQUESTS)

    return HttpResponse(200)


def _create_agreement_form_list(project, user, current_step):

    # Order by name descending temporarily so the n2c2 ROC appears before DUA
    agreement_forms = project.agreement_forms.order_by('-name')

    agreement_forms_list = []

    for agreement_form in agreement_forms:
        signed_agreement_forms = SignedAgreementForm.objects.filter(project=project,
                                                                    user=user,
                                                                    agreement_form=agreement_form,
                                                                    status__in=["P", "A"])

        if signed_agreement_forms.count() > 0:
            already_signed = True
        else:
            already_signed = False

        if current_step is None and not already_signed:
            current_step = agreement_form.name

        agreement_forms_list.append({'agreement_form_name': agreement_form.name,
                                     'agreement_form_id': agreement_form.id,
                                     'agreement_form_path': agreement_form.form_file_path,
                                     'already_signed': already_signed})
    return agreement_forms_list, current_step


def _project_access_request(user_access_requests, project):

    if user_access_requests is not None and 'results' in user_access_requests:
        user_access_requests = user_access_requests["results"]
        for access_request in user_access_requests:
            if access_request["item"] == project.project_key:
                return access_request

    return None


@public_user_auth_and_jwt
def project_details(request, project_key):

    if not request.user.is_authenticated():
        project = get_object_or_404(DataProject, project_key=project_key, visible=True)
        return render(request, 'project_login_or_register.html', {'project': project})

    current_step = None
    user = request.user

    if user.is_superuser:
        project = get_object_or_404(DataProject, project_key=project_key)
    else:
        project = get_object_or_404(DataProject, project_key=project_key, visible=True)

    user_jwt = request.COOKIES.get("DBMI_JWT", None)

    # If for some reason they have a session but not JWT, force them to log in again.
    if user_jwt is None or validate_jwt(request) is None:
        return logout_redirect(request)

    sciauthz = SciAuthZ(settings.AUTHZ_BASE, user_jwt, user.email)
    is_manager = sciauthz.user_has_manage_permission(project_key)
    user_access_requests = sciauthz.current_user_access_requests()
    user_access_request = _project_access_request(user_access_requests, project)

    # Check for a returning task and set messages accordingly
    get_task_context_data(request)

    # Make a request to SciReg to grab email verification and profile information
    profile_registration_info = get_current_user_profile(user_jwt)

    if profile_registration_info.get('count', 0) != 0:
        profile_registration_info = profile_registration_info["results"][0]
        email_verified = profile_registration_info['email_confirmed']

        # Do not bind the form, otherwise it will present the user with validation markup (green/red stuff) which can be overwhelming
        registration_form = RegistrationForm(initial=profile_registration_info)

        # Check to see if any of the required fields are not populated yet
        profile_completed = True
        for field in registration_form.fields:
            if registration_form.fields[field].required and profile_registration_info[field] == "":
                profile_completed = False

    else:
        # User does not have a registration in scireg, present them with a blank form to complete and pre-populate the email
        registration_form = RegistrationForm(initial={'email': user.email}, new_registration=True)
        email_verified = False
        profile_completed = False

    if current_step is None and not email_verified:
        current_step = "verify_email"

    if current_step is None and not profile_completed:
        current_step = "complete_profile"

    if current_step is None and profile_completed and project.show_jwt:
        current_step = "jwt"

    # Check to see if any of the agreement forms have been signed and not rejected by an admin
    agreement_forms_list, current_step = _create_agreement_form_list(project, user, current_step)

    try:
        # Only allow a user onto the project participation page if they are on an Active team and they have VIEW permissions
        participant = Participant.objects.get(user=user)
        team = participant.team
        access_granted = participant.team_approved and team.status == 'Active' and sciauthz.user_has_single_permission("n2c2-t1", "VIEW")
    except ObjectDoesNotExist:
        participant = None
        team = None
        access_granted = False

    team_has_pending_members = Participant.objects.filter(team=team, team_approved=False)

    # If all other steps completed, then last step will be team
    if current_step is None and not project.is_contest:
        current_step = "request_access"
    elif current_step is None:
        current_step = "team"

    final_signed_agreement_forms = SignedAgreementForm.objects.filter(project=project,
                                                                      user=user,
                                                                      status__in=["P", "A"])
    context = {"project": project,
               "agreement_forms_list": agreement_forms_list,
               "participant": participant,
               "team": team,
               "team_has_pending_members": team_has_pending_members,
               "is_manager": is_manager,
               "email_verified": email_verified,
               "profile_completed": profile_completed,
               "institution": project.institution,
               "registration_form": registration_form,
               "current_step": current_step,
               "final_signed_agreement_forms": final_signed_agreement_forms,
               "user_jwt": user_jwt,
               "user_access_request": user_access_request}

    if not access_granted or not project.is_contest:
        return render(request, 'project_signup.html', context)
    else:
        return render(request, 'project_participate.html', context)




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

        # Get super's context.
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
        Include all common context items here. Initiates the steps list. Each step
        is a dictionary holding information about how to render the step. A step
        should include a title, a template to render, and a status.
        """

        # Add the project to the context.
        context['project'] = self.project

        # Initialize the steps list.
        context['steps'] = []

        # Initialize tracking of which step is the current step.
        context['current_step'] = None

        # Check if the user is a manager of this DataProject.
        sciauthz = SciAuthZ(settings.AUTHZ_BASE, self.user_jwt, self.request.user.email)
        context['is_manager'] = sciauthz.user_has_manage_permission(self.project.project_key)
        context['has_view_permission'] = sciauthz.user_has_single_permission(self.project.project_key, "VIEW")

    def get_unregistered_context(self, context):
        """
        Adds to the view's context anything needed for unregistered users to
        be able to learn about this DataProject.
        """

        # Set the template that should be rendered.
        self.template_name = 'project_login_or_register.html'

        return context

    def get_signup_context(self, context):
        """
        Adds to the view's context anything needed for users to get access to
        this DataProject.
        """

        # Verify email step.
        self.step_verify_email(context)

        # SciReg complete profile step.
        self.step_complete_profile(context)

        # Agreement forms step (if needed).
        self.step_sign_agreement_forms(context)

        # Team setup step (if needed).
        self.step_setup_team(context)

        # Set the template that should be rendered.
        self.template_name = 'project_signup.html'

        return context

    def get_participate_context(self, context):
        """
        Adds to the view's context anything needed for participating in a DataProject
        once a user has been granted access to it.
        """

        # Set the template that should be rendered.
        self.template_name = ''

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

        # Describe the step.
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

        context['registration_form'] = registration_form

        step_status = self.get_step_status(context, 'complete_profile', profile_complete)

        # Describe the step.
        step = {
            'title': 'Complete Your Profile',
            'template': 'project_signup/complete_profile.html',
            'status': step_status
        }

        context['steps'].append(step)

    def step_sign_agreement_forms(self, context):
        """
        Builds the context needed for users to complete any required agreement forms.
        This is an optional step depending on the data project. One step will be added
        for each agreement form required by this DataProject.
        """

        # Do not include this step if this project does not have any agreement forms.
        if self.project.agreement_forms.count() == 0:
            return

        agreement_forms = self.project.agreement_forms.order_by('-name')

        # Each form will be a separate step.
        for form in agreement_forms:

            # Only include Pending or Approved forms when searching.
            signed_forms = SignedAgreementForm.objects.filter(
                user=self.request.user,
                project=self.project,
                agreement_form=form,
                status__in=["P", "A"]
            )

            complete = signed_forms.count() > 0
            status = self.get_step_status(context, form.short_name, complete)

            # Describe the step.
            step = {
                'title': 'Form: {name}'.format(name=form.name),
                'template': 'project_signup/sign_agreement_form.html',
                'status': status,
                'agreement_form': form
            }

            context['steps'].append(step)

    def step_setup_team(self, context):
        """
        Builds the context needed for users to create or join a team. This is an
        optional step depending on the data project.
        """

        # Do not include this step if this project does not involve teams.
        if not self.project.has_teams:
            return

        # If a user has a Participant record, then they have already been associated
        # with a team.
        if self.participant is not None:
            context['participant'] = self.participant
            context['team'] = self.participant.team

            context['team_has_pending_members'] = Participant.objects.filter(
                team=self.participant.team,
                team_approved=False
            )

        # This step is never completed.
        status = self.get_step_status(context, 'setup_team', False)

        # Describe the step.
        step = {
            'title': 'Join or Create a Team',
            'template': 'project_signup/setup_team.html',
            'status': status
        }

        context['steps'].append(step)

    def is_user_granted_access(self, context):
        """
        Determines whether or not a user has met all the necessary requirements to be
        considered having been granted access to participate in this DataProject.
        """

        # Check for VIEW permissions in SciAuthZ.
        if not context['has_view_permission'] or not context['is_manager']:
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
