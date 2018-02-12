import logging

from django.shortcuts import render
from django.shortcuts import redirect
from django.http import HttpResponse
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.models import User

from .models import DataProject
from .models import Participant
from .models import Team

from pyauth0jwt.auth0authenticate import user_auth_and_jwt

logger = logging.getLogger(__name__)

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
def join_team(request):
    project_key = request.POST.get("project_key")
    project = DataProject.objects.get(project_key=project_key)

    existing_pi_team_to_join = request.POST.get("existing_pi_team_to_join")
    pi_to_wait_for = request.POST.get("pi_to_wait_for")

    try:
        participant = Participant.objects.get(user=request.user)
    except ObjectDoesNotExist:
        participant = create_participant(request.user, project)

    if pi_to_wait_for != "":
        participant.team_wait_on_leader_email = pi_to_wait_for
        participant.team_wait_on_leader = True
        participant.save()
    elif existing_pi_team_to_join != "":
        try:
            team = Team.objects.get(team_leader__email=existing_pi_team_to_join)
        except ObjectDoesNotExist:
            team = None

        participant.team = team
        participant.team_pending = True
        participant.save()

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
def create_team_from_pi(request):
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
