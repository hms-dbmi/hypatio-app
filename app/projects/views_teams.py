import logging

from django.shortcuts import render
from django.shortcuts import redirect

from django.core.exceptions import ObjectDoesNotExist

from .models import DataProject
from .models import Participant
from .models import Team

from pyauth0jwt.auth0authenticate import user_auth_and_jwt

logger = logging.getLogger(__name__)


@user_auth_and_jwt
def join_team(request):
    project_key = request.POST.get("project_key")

    join_team_pi = request.POST.get("join_pi")

    try:
        participant = Participant.objects.get(user=request.user)
    except ObjectDoesNotExist:
        participant = None

    if request.POST.get("join_email") != "":
        participant.team_wait_on_pi_email = request.POST.get("join_email")
        participant.team_wait_on_pi = True

        participant.save()
    elif request.POST.get("join_pi") != "":
        try:
            team = Team.objects.get(principal_investigator__email=join_team_pi)
        except ObjectDoesNotExist:
            team = None

        participant.team = team
        participant.team_pending = True
        participant.save()

    return redirect('/projects/' + request.POST.get('project_key') + '/')


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
    project_key = request.POST.get("project_key")
    project = DataProject.objects.get(project_key=project_key)
    new_team = Team.objects.create(principal_investigator=request.user, data_project=project)

    # Assign yourself to team.
    participant = Participant.objects.get(user=request.user)
    participant.team = new_team
    participant.team_wait_on_pi = False
    participant.team_pending = False
    participant.team_approved = True
    participant.save()

    return redirect('/projects/' + project_key + '/')