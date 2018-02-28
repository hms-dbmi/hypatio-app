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

from pyauth0jwt.auth0authenticate import user_auth_and_jwt
from pyauth0jwt.auth0authenticate import public_user_auth_and_jwt
from pyauth0jwt.auth0authenticate import validate_jwt
from pyauth0jwt.auth0authenticate import logout_redirect

from .models import DataProject
from .models import Participant
from .models import Team
from .models import AgreementForm
from .models import SignedAgreementForm

from profile.views import get_task_context_data
from profile.forms import RegistrationForm

from django.http import HttpResponse
from django.core.exceptions import ObjectDoesNotExist

from hypatio.sciauthz_services import SciAuthZ
from hypatio.scireg_services import get_user_profile


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
def download_signed_form(request):

    user_jwt = request.COOKIES.get("DBMI_JWT", None)

    project_key = request.GET['project_key']
    signed_agreement_form_id = request.GET['signed_form_id']

    sciauthz = SciAuthZ(settings.AUTHZ_BASE, user_jwt, request.user.email)
    is_manager = sciauthz.user_has_manage_permission(request, project_key)

    if is_manager:
        project = get_object_or_404(DataProject, project_key=project_key)
        signed_agreement_form = get_object_or_404(SignedAgreementForm, id=signed_agreement_form_id, project=project)
        return HttpResponse(signed_agreement_form.agreement_text, content_type='text/plain')
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
        user_logged_in = False
    else:
        user = request.user
        user_logged_in = True
        user_jwt = request.COOKIES.get("DBMI_JWT", None)

        # If for some reason they have a session but not JWT, force them to log in again.
        if user_jwt is None or validate_jwt(request) is None:
            return logout_redirect(request)

        sciauthz = SciAuthZ(settings.AUTHZ_BASE, user_jwt, user.email)
        is_manager = sciauthz.user_has_manage_permission(request, 'Hypatio.n2c2-t1')
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
                                           "user_logged_in": user_logged_in,
                                           "user": user,
                                           "ssl_setting": settings.SSL_SETTING,
                                           "is_manager": is_manager,
                                           "account_server_url": settings.ACCOUNT_SERVER_URL,
                                           "profile_server_url": settings.SCIREG_SERVER_URL})

@public_user_auth_and_jwt
def list_data_contests(request, template_name='datacontests/list.html'):

    all_data_contests = DataProject.objects.filter(is_contest=True, visible=True)
    data_contests = []

    is_manager = False

    if not request.user.is_authenticated():
        user = None
        user_logged_in = False
    else:

        user = request.user
        user_logged_in = True
        user_jwt = request.COOKIES.get("DBMI_JWT", None)

        # If for some reason they have a session but not JWT, force them to log in again.
        if user_jwt is None or validate_jwt(request) is None:
            return logout_redirect(request)

        if request.user.is_superuser:
            all_data_contests = DataProject.objects.filter(is_contest=True)

        sciauthz = SciAuthZ(settings.AUTHZ_BASE, user_jwt, user.email)
        is_manager = sciauthz.user_has_manage_permission(request, 'Hypatio.n2c2-t1')

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
                                           "user_logged_in": user_logged_in,
                                           "user": user,
                                           "ssl_setting": settings.SSL_SETTING,
                                           "is_manager": is_manager,
                                           "account_server_url": settings.ACCOUNT_SERVER_URL,
                                           "profile_server_url": settings.SCIREG_SERVER_URL})

@user_auth_and_jwt
def view_team_management(request, template_name='datacontests/manageteams.html'):
    """
    Populates the team management modal popup on the contest management screen.
    """

    project_key = request.GET["project"]
    team_leader = request.GET["team"]

    project = DataProject.objects.get(project_key=project_key)
    team = Team.objects.get(data_project=project, team_leader__email=team_leader)
    num_required_forms = project.agreement_forms.count()

    user_jwt = request.COOKIES.get("DBMI_JWT", None)

    # Collect all the team member information needed
    team_members = []

    for member in team.participant_set.all():
        email = member.user.email

        # Make a request to SciReg for a specific person's user information
        user_info_json = get_user_profile(user_jwt, email, project_key)

        if user_info_json['count'] != 0:
            user_info = user_info_json["results"][0]
        else:
            user_info = None
        
        signed_agreement_forms = SignedAgreementForm.objects.filter(user__email=email, project=project)

        team_members.append({
            'email': email,
            'user_info': user_info,
            'signed_agreement_forms': signed_agreement_forms,
            'participant': member
        })

    return render(request, template_name, context={"project": project,
                                                   "team": team,
                                                   "team_members": team_members,
                                                   "num_required_forms": num_required_forms})

@user_auth_and_jwt
def manage_contest(request, project_key, template_name='datacontests/managecontests.html'):

    project = DataProject.objects.get(project_key=project_key)

    # This dictionary will hold all user requests and permissions
    user_details = {}

    user = request.user
    user_logged_in = True
    user_jwt = request.COOKIES.get("DBMI_JWT", None)

    sciauthz = SciAuthZ(settings.AUTHZ_BASE, user_jwt, user.email)
    is_manager = sciauthz.user_has_manage_permission(request, project_key)

    if not is_manager:
        logger.debug('[HYPATIO][DEBUG] User ' + user.email + ' does not have MANAGE permissions for item ' + project_key + '.')
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

        # Make a request to SciReg for a specific person's user information
        user_info_json = get_user_profile(user_jwt, email, project_key)

        if user_info_json['count'] != 0:
            user_info = user_info_json["results"][0]
        else:
            user_info = None
        
        signed_agreement_forms = SignedAgreementForm.objects.filter(user__email=email, project=project)

        users_without_a_team_details.append({
            'email': email,
            'user_info': user_info,
            'signed_agreement_forms': signed_agreement_forms,
            'participant': person
        })

    # Simple statistics for display
    total_teams = teams.count()
    total_participants = Participant.objects.filter(data_challenge=project).count()   
    countries_represented = '?' # TODO
    total_submissions = 0 # TODO
    teams_with_any_submission = 0 # TODO

    return render(request, template_name, {"user_logged_in": user_logged_in,
                                           "user": user,
                                           "ssl_setting": settings.SSL_SETTING,
                                           "is_manager": is_manager,
                                           "project": project,
                                           "teams": teams,
                                           "users_without_a_team_details": users_without_a_team_details,
                                           "total_teams": total_teams,
                                           "total_participants": total_participants,
                                           "countries_represented": countries_represented,
                                           "total_submissions": total_submissions,
                                           "teams_with_any_submission": teams_with_any_submission})

# TODO remove this: activate_team view should now do this
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
    is_manager = sciauthz.user_has_manage_permission(request, project)

    if not is_manager:
        logger.debug('[HYPATIO][DEBUG] User ' + user.email + ' does not have MANAGE permissions for item ' + project + '.')
        return HttpResponse(403)

    # Grab the full authorization request object from SciAuthZ to have all fields necessary for serialization
    authorization_request_url = settings.AUTHORIZATION_REQUEST_URL + "?id=" + authorization_request_id
    authorization_request = requests.get(authorization_request_url, headers=jwt_headers, verify=False).json()

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
    requests.put(authorization_request_url, headers=jwt_headers, data=json.dumps(authorization_request_data), verify=False)

    user_permission = {"user": person_email,
                       "item": project,
                       "permission": "VIEW",
                       "date_updated": current_time}

    # Add a VIEW permission to the user
    permissions_url = settings.USER_PERMISSIONS_URL
    user_permissions = requests.post(permissions_url, headers=jwt_headers, data=json.dumps(user_permission), verify=False)

    return HttpResponse(200)

@public_user_auth_and_jwt
def project_details(request, project_key, template_name='project_details.html'):

    # TODO cleanup and eliminate some of these where possible
    registration_form = None
    agreement_forms_list = []
    participant = None
    is_manager = False
    user_requested_access = False
    user_access_request_granted = False
    email_verified = False
    profile_completed = False
    team = None
    team_members = None
    team_has_pending_members = None
    user_is_team_leader = False
    access_granted = False
    current_step = None

    if not request.user.is_authenticated():
        user = None
        user_logged_in = False

        project = get_object_or_404(DataProject, project_key=project_key, visible=True)

    else:
        user = request.user

        if user.is_superuser:
            project = get_object_or_404(DataProject, project_key=project_key)
        else:
            project = get_object_or_404(DataProject, project_key=project_key, visible=True)

        user_logged_in = True
        user_jwt = request.COOKIES.get("DBMI_JWT", None)

        # If for some reason they have a session but not JWT, force them to log in again.
        if user_jwt is None or validate_jwt(request) is None:
            return logout_redirect(request)

        sciauthz = SciAuthZ(settings.AUTHZ_BASE, user_jwt, user.email)
        is_manager = sciauthz.user_has_manage_permission(request, project_key)

        # The JWT token that will get passed in API calls
        jwt_headers = {"Authorization": "JWT " + user_jwt, 'Content-Type': 'application/json'}

        # Check for a returning task and set messages accordingly
        get_task_context_data(request)

        # Make a request to SciReg to grab email verification and profile information
        profile_registration_info = requests.get(settings.SCIREG_REGISTRATION_URL, headers=jwt_headers, verify=False).json()

        if profile_registration_info['count'] != 0:
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

        # Order by name descending temporarily so the n2c2 ROC appears before DUA
        agreement_forms = project.agreement_forms.order_by('-name')

        # Check to see if any of the necessary agreement forms have already been signed by the user
        for agreement_form in agreement_forms:
            signed_agreement_form = SignedAgreementForm.objects.filter(project=project,
                                                                       user=user,
                                                                       agreement_form=agreement_form)

            if signed_agreement_form.count() > 0:
                already_signed = True
            else:
                already_signed = False
            
            if current_step is None and not already_signed:
                current_step = agreement_form.name

            agreement_forms_list.append({'agreement_form_name': agreement_form.name,
                                         'agreement_form_id': agreement_form.id,
                                         'agreement_form_file': agreement_form.form_html.name,
                                         'already_signed': already_signed})

        try:
            participant = Participant.objects.get(user=user)
            team = participant.team
        except ObjectDoesNotExist:
            participant = None
            team = None

        if participant and team:
            team_members = Participant.objects.filter(team=team)
            team_has_pending_members = team_members.filter(team_approved=False)
            user_is_team_leader = team.team_leader == request.user

        if team and team.status == 'Active':
            access_granted = True

        # If all other steps completed, then last step will be team
        if current_step is None:
            current_step = "team"

        # Get all of the user's permission requests
        access_requests_url = settings.AUTHORIZATION_REQUEST_URL + "?email=" + user.email
        logger.debug('[HYPATIO][DEBUG] access_requests_url: ' + access_requests_url)

        user_access_requests = requests.get(access_requests_url, headers=jwt_headers, verify=False).json()
        logger.debug('[HYPATIO][DEBUG] User Permission Requests: ' + json.dumps(user_access_requests))

        if user_access_requests is not None and 'results' in user_access_requests:
            for access_request in user_access_requests['results']:
                if access_request['item'] == project_key:
                    user_requested_access = True
                    user_access_request_granted = access_request['request_granted']

    institution = project.institution

    return render(request, template_name, {"project": project,
                                           "agreement_forms_list": agreement_forms_list,
                                           "participant": participant,
                                           "team": team,
                                           "user_is_team_leader": user_is_team_leader,
                                           "team_members": team_members,
                                           "team_has_pending_members": team_has_pending_members,
                                           "access_granted": access_granted,
                                           "is_manager": is_manager,
                                           "user_logged_in": user_logged_in,
                                           "user_requested_access": user_requested_access,
                                           "user_access_request_granted": user_access_request_granted,
                                           "email_verified": email_verified,
                                           "profile_completed": profile_completed,
                                           "institution": institution,
                                           "registration_form": registration_form,
                                           "current_step": current_step})
