import logging

from django.shortcuts import render
from django.shortcuts import redirect
from django.http import HttpResponse
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.models import User
from django.conf import settings

from hypatio.sciauthz_services import SciAuthZ

from .models import DataProject
from .models import Participant
from .models import Team
from .models import SignedAgreementForm
from .models import TeamComment

from contact.views import email_send

from pyauth0jwt.auth0authenticate import user_auth_and_jwt

logger = logging.getLogger(__name__)

@user_auth_and_jwt
def save_team_comment(request):
    """Saves a comment made about a team by a challenge administrator."""

    project_key = request.POST.get("project")
    team_leader = request.POST.get("team")
    comment = request.POST.get("comment")

    logger.debug('[HYPATIO][save_team_comment] ' + request.user.email + ' entered a comment about team ' + team_leader + '.')

    project = DataProject.objects.get(project_key=project_key)
    team = Team.objects.get(team_leader__email=team_leader, data_project=project)

    new_comment = TeamComment(user=request.user,
                              team=team,
                              text=comment)
    new_comment.save()

    return HttpResponse(200)

@user_auth_and_jwt
def change_team_status(request):
    """Change a team's status, assign the correct permissions, and notify team members."""

    project_key = request.POST.get("project")
    team_leader = request.POST.get("team")
    status = request.POST.get("status")

    logger.debug('[HYPATIO][change_team_status] ' + request.user.email + ' changing team ' + team_leader + ' for project ' + project_key + ' to status of ' + status + '.')

    project = DataProject.objects.get(project_key=project_key)
    team = Team.objects.get(team_leader__email=team_leader, data_project=project)

    # First change the team's status
    if status == "pending":
        team.status = "Pending"
        team.save()
    elif status == "ready":
        team.status = "Ready"
        team.save()
    elif status == "active":
        team.status = "Active"
        team.save()
    elif status == "deactivated":
        team.status = "Deactivated"
        team.save()
    else:
        logger.debug('[HYPATIO][change_team_status] Given status "' + status + '" not one of allowed statuses.')
        return HttpResponse(500)

    logger.debug('[HYPATIO][change_team_status] Adjusting VIEW permissions for team members.')

    # If a status is anything other than active, remove VIEW permissions
    if status in ["active"]:
        for member in team.participant_set.all():
            sciauthz = SciAuthZ(settings.AUTHZ_BASE, request.COOKIES.get("DBMI_JWT", None), request.user.email)
            sciauthz.create_view_permission(project_key, member.user.email)
    else:
        for member in team.participant_set.all():
            sciauthz = SciAuthZ(settings.AUTHZ_BASE, request.COOKIES.get("DBMI_JWT", None), request.user.email)
            sciauthz.remove_view_permission(project_key, member.user.email)

    logger.debug('[HYPATIO][change_team_status] Emailing a notification to team members.')

    # Send an email notification to the team
    context = {'status': status,
               'project': project,
               'site_url': settings.SITE_URL}

    # Email list
    emails = [member.user.email for member in team.participant_set.all()]

    email_success = email_send(subject='DBMI Portal Team Status Changed',
                               recipients=emails,
                               email_template='email_new_team_status_notification',
                               extra=context)

    return HttpResponse(200)

@user_auth_and_jwt
def delete_team(request):
    """Delete a team and notify members."""

    project_key = request.POST.get("project")
    team_leader = request.POST.get("team")
    administrator_message = request.POST.get("administrator_message")

    logger.debug('[HYPATIO][delete_team] ' + request.user.email + ' is deleting team ' + team_leader + ' for project ' + project_key + '.')

    project = DataProject.objects.get(project_key=project_key)
    team = Team.objects.get(team_leader__email=team_leader, data_project=project)

    logger.debug('[HYPATIO][delete_team] Removing all VIEW permissions for team members.')

    # First revoke all VIEW permissions
    for member in team.participant_set.all():
        sciauthz = SciAuthZ(settings.AUTHZ_BASE, request.COOKIES.get("DBMI_JWT", None), request.user.email)
        sciauthz.remove_view_permission(project_key, member.user.email)

    logger.debug('[HYPATIO][delete_team] Sending a notification to team members.')

    # Then send a notification to the team members
    context = {'administrator_message': administrator_message,
               'project': project,
               'site_url': settings.SITE_URL}

    emails = [member.user.email for member in team.participant_set.all()]

    email_success = email_send(subject='DBMI Portal Team Deleted',
                               recipients=emails,
                               email_template='email_team_deleted_notification',
                               extra=context)

    logger.debug('[HYPATIO][delete_team] Deleting the team from the database.')

    # Then delete the team
    team.delete()

    logger.debug('[HYPATIO][delete_team] Team ' + team_leader + ' for project ' + project_key + ' successfully deleted.')

    return HttpResponse(200)

@user_auth_and_jwt
def finalize_team(request):
    """Mark the team as ready and send an email notification to contest managers."""

    project_key = request.POST.get("project_key")
    team = request.POST.get("team")

    project = DataProject.objects.get(project_key=project_key)
    team = Team.objects.get(team_leader__email=team, data_project=project)

    team.status = 'Ready'
    team.save()

    # TODO Eventually this should be replaced by checking SciAuthZ for MANAGE permissions
    contest_managers = ['ouzuner@gmu.edu', 'filannim@csail.mit.edu', 'stubbs@simmons.edu']

    context = {'team_leader': team,
               'project': project_key,
               'site_url': settings.SITE_URL}

    email_success = email_send(subject='DBMI Portal Finalized Team',
                               recipients=contest_managers,
                               email_template='email_finalized_team_notification',
                               extra=context)

    return HttpResponse(200)

@user_auth_and_jwt
def approve_team_join(request):
    project_key = request.POST.get("project_key")
    participant_email = request.POST.get("participant")

    project = DataProject.objects.get(project_key=project_key)

    try:
        team = Team.objects.get(team_leader=request.user,
                                data_project=project)
    except ObjectDoesNotExist:
        team = None

    try:
        participant_user = User.objects.get(email=participant_email)
        participant = Participant.objects.get(user=participant_user,
                                              data_challenge=project)
    except ObjectDoesNotExist:
        participant = None

    participant.assign_approved(team)
    participant.save()

    return HttpResponse(200)

@user_auth_and_jwt
def reject_team_join(request):
    project_key = request.POST.get("project_key")
    participant_email = request.POST.get("participant")

    project = DataProject.objects.get(project_key=project_key)

    try:
        participant_user = User.objects.get(email=participant_email)
        participant = Participant.objects.get(user=participant_user,
                                              data_challenge=project)
        participant.delete()
    except ObjectDoesNotExist:
        participant = None

    return HttpResponse(200)

@user_auth_and_jwt
def leave_team(request):
    project_key = request.POST.get("project_key")
    project = DataProject.objects.get(project_key=project_key)

    team_leader = request.POST.get("team_leader")

    participant = Participant.objects.get(user=request.user)
    participant.team = None
    participant.pending = False
    participant.approved = False
    participant.team_wait_on_leader_email = None
    participant.team_wait_on_leader = False
    participant.save()

    return redirect('/projects/' + request.POST.get('project_key') + '/')

@user_auth_and_jwt
def join_team(request):
    project_key = request.POST.get("project_key")
    project = DataProject.objects.get(project_key=project_key)

    team_leader = request.POST.get("team_leader")

    try:
        participant = Participant.objects.get(user=request.user)
    except ObjectDoesNotExist:
        participant = create_participant(request.user, project)

    try:
        # If this team leader has already created a team, add the person to the team in a pending status
        team = Team.objects.get(team_leader__email__iexact=team_leader)
        participant.team = team
        participant.team_pending = True
        participant.save()
    except ObjectDoesNotExist:
        # If this team leader has not yet created a team, mark the person as waiting
        participant.team_wait_on_leader_email = team_leader
        participant.team_wait_on_leader = True
        participant.save()
        team = None

    # Send email to team leader informing them of a pending member
    if team is not None:
        context = {'member_email': request.user.email,
                   'project': project,
                   'site_url': settings.SITE_URL}

        email_success = email_send(subject='DBMI Portal - Finalized Team',
                                   recipients=[team_leader],
                                   email_template='email_pending_member_notification',
                                   extra=context)

    logger.debug('[HYPATIO][join_team] - Creating Profile Permissions')

    # Create record to allow leader access to profile.
    sciauthz = SciAuthZ(settings.AUTHZ_BASE, request.COOKIES.get("DBMI_JWT", None), request.user.email)
    sciauthz.create_profile_permission(team_leader)

    return redirect('/projects/' + request.POST.get('project_key') + '/')

# TODO What is this used for?
@user_auth_and_jwt
def team_signup_form(request, project_key):

    try:
        participant = Participant.objects.get(user=request.user)
    except ObjectDoesNotExist:
        participant = None

    try:
        teams = Team.objects.get(data_project__project_key=project_key)
    except ObjectDoesNotExist:
        teams = None

    return render(request, "teams/manageteam.html", {"participant": participant,
                                                     "teams": teams})

@user_auth_and_jwt
def create_team(request):
    """Creates a new team with the given user as its team leader.
    """

    project_key = request.POST.get("project_key")
    project = DataProject.objects.get(project_key=project_key)
    new_team = Team.objects.create(team_leader=request.user, data_project=project)

    try:
        participant = Participant.objects.get(user=request.user, data_challenge=project)
    except ObjectDoesNotExist:
        participant = create_participant(request.user, project)

    participant.assign_approved(new_team)
    participant.save()

    # Find anyone whose waiting on this team leaedear and link them to the new team.
    waiting_participants = Participant.objects.filter(team_wait_on_leader_email=request.user.email)

    for participant in waiting_participants:
        participant.assign_pending(new_team)
        participant.save()

    return redirect('/projects/' + project_key + '/')

def create_participant(user, project):
    """ Creates a participant object and returns it.
    """

    participant = Participant(user=user,
                              data_challenge=project)
    participant.save()

    return participant
