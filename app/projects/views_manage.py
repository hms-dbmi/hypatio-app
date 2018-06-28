import logging

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
from django.contrib.auth.models import User

from pyauth0jwt.auth0authenticate import user_auth_and_jwt

from hypatio.sciauthz_services import SciAuthZ

from .models import DataProject
from .models import Team
from .models import TeamComment
from .models import SignedAgreementForm
from .models import HostedFile
from .models import HostedFileDownload
from .models import Participant
from .models import ParticipantSubmission

from hypatio.scireg_services import get_distinct_countries_participating
from hypatio.scireg_services import get_user_profile

# Get an instance of a logger
logger = logging.getLogger(__name__)


@user_auth_and_jwt
def manage_project(request, project_key, template_name='manage/manageprojects.html'):

    user = request.user
    user_jwt = request.COOKIES.get("DBMI_JWT", None)

    sciauthz = SciAuthZ(settings.AUTHZ_BASE, user_jwt, user.email)
    is_manager = sciauthz.user_has_manage_permission(project_key)
    has_manage_permissions = sciauthz.user_has_any_manage_permissions()

    project = DataProject.objects.get(project_key=project_key)

    if not is_manager:
        logger.debug(
            '[HYPATIO][DEBUG][manage_team] User ' + user.email + ' does not have MANAGE permissions for item ' + project_key + '.')
        return HttpResponse(403)

    teams = Team.objects.filter(data_project=project)

    return render(request, template_name, context={"user": user,
                                                   "has_manage_permissions": has_manage_permissions,
                                                   "project": project,
                                                   "teams": teams,
                                                   })

#TODO: Use this more widely.
def prepare_participant_details(participants, user_jwt, project):

    team_member_details = []
    team_accepted_forms = 0

    for member in participants:
        email = member.user.email

        # Make a request to SciReg for a specific person's user information
        user_info_json = get_user_profile(user_jwt, email, project.project_key)

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

    return team_member_details, team_accepted_forms


@user_auth_and_jwt
def manage_project_team(request, project_key, team_leader, template_name='manage/manage_project_teams.html'):

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
    team_participants = team.participant_set.all()
    team_member_details, team_accepted_forms = prepare_participant_details(team_participants, user_jwt, project)

    # Check whether this team has completed all the necessary forms and they have been accepted by challenge admins
    total_required_forms_for_team = project.agreement_forms.count() * team_participants.count()
    team_has_all_forms_complete = total_required_forms_for_team == team_accepted_forms

    institution = project.institution

    # Get the comments made about this team by challenge administrators
    comments = TeamComment.objects.filter(team=team)

    return render(request, template_name, context={"user": user,
                                                   "ssl_setting": settings.SSL_SETTING,
                                                   "has_manage_permissions": has_manage_permissions,
                                                   "project": project,
                                                   "team": team,
                                                   "team_members": team_member_details,
                                                   "num_required_forms": num_required_forms,
                                                   "team_has_all_forms_complete": team_has_all_forms_complete,
                                                   "institution": institution,
                                                   "comments": comments})


@user_auth_and_jwt
def manage_team(request, project_key, team_leader, template_name='datacontests/manageteams.html'):
    """
    Populates the team management modal popup on the contest management screen.
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
def manage_contest(request, project_key, template_name='datacontests/managecontests.html'):
    project = DataProject.objects.get(project_key=project_key)

    # This dictionary will hold all user requests and permissions
    user_details = {}

    user = request.user
    user_jwt = request.COOKIES.get("DBMI_JWT", None)

    sciauthz = SciAuthZ(settings.AUTHZ_BASE, user_jwt, user.email)
    is_manager = sciauthz.user_has_manage_permission(project_key)
    has_manage_permissions = sciauthz.user_has_any_manage_permissions()

    if not is_manager:
        logger.debug(
            '[HYPATIO][DEBUG][manage_contest] User ' + user.email + ' does not have MANAGE permissions for item ' + project_key + '.')
        return HttpResponse(403)

    teams = Team.objects.filter(data_project=project)

    # A person who has filled out a form for a project but not yet joined a team
    users_with_a_team = Participant.objects.filter(team__in=teams).values_list('user', flat=True).distinct()
    users_who_signed_forms = SignedAgreementForm.objects.filter(project=project).values_list('user',
                                                                                             flat=True).distinct()
    users_without_a_team = User.objects.filter(id__in=users_who_signed_forms).exclude(id__in=users_with_a_team)

    # Collect additional information about these participants who aren't on teams yet
    users_without_a_team_details = []

    for person in users_without_a_team:
        email = person.email

        signed_agreement_forms = []

        # For each of the available agreement forms for this project, display only latest version completed by the user
        for agreement_form in project.agreement_forms.all():
            signed_agreement_forms.append(SignedAgreementForm.objects.filter(user__email=email, project=project,
                                                                             agreement_form=agreement_form).last())

        users_without_a_team_details.append({
            'email': email,
            # 'user_info': user_info,
            'signed_agreement_forms': signed_agreement_forms,
            'participant': person
        })

    approved_teams = teams.filter(status='Active')

    approved_participants = Participant.objects.filter(team__in=approved_teams)

    all_submissions = ParticipantSubmission.objects.filter(
        participant__in=approved_participants,
        deleted=False
    )

    teams_with_any_submission = all_submissions.values('participant__team').distinct()

    countries = get_distinct_countries_participating(user_jwt, approved_participants, project_key)

    institution = project.institution

    return render(request, template_name, {"user": user,
                                           "ssl_setting": settings.SSL_SETTING,
                                           "has_manage_permissions": has_manage_permissions,
                                           "project": project,
                                           "teams": teams,
                                           "users_without_a_team_details": users_without_a_team_details,
                                           "approved_teams": approved_teams.count(),
                                           "approved_participants": approved_participants.count(),
                                           "total_submissions": all_submissions.count(),
                                           "teams_with_any_submission": teams_with_any_submission.count(),
                                           "participating_countries": countries,
                                           "institution": institution})

