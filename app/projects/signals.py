from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction

from projects.models import DataProject
from projects.models import Team
from projects.models import Participant
from projects.models import TEAM_ACTIVE, TEAM_DEACTIVATED, TEAM_READY

import logging
logger = logging.getLogger(__name__)


@receiver(post_save, sender=DataProject)
def dataproject_post_save_handler(sender, **kwargs):
    """
    This hook listens for DataProjects that have been saved and handles the
    syncing of Teams if team sharing has been specified.
    """
    instance = kwargs.get("instance")

    # Check if this project requires importing of teams
    if instance.teams_source:
        logger.debug(f"Project uses teams from: {instance.teams_source}")

        # Sync
        sync_teams(instance.teams_source)

@receiver(post_save, sender=Team)
def team_post_save_handler(sender, **kwargs):
    """
    This hook listens for Team modifications and appropriately propogates
    properties if this team is a source for other DataProject teams.
    """
    instance = kwargs.get("instance")

    # Check if this is a shared team
    if instance.data_project.shares_teams:
        logger.debug(f"Team is a source for other projects: {instance}")

        # Sync
        sync_teams(instance.data_project)


def sync_teams(project):
    """
    This method accepts a project and performs a sync of the project's teams
    and participants. If this project shares teams, all ACTIVE teams and their
    corresponding participants will be duplicated for all projects that use
    this project as their team source. Existing teams will also be checked for
    access revocations if they are unapproved for the source project as that
    change is automatically propogated out to sharing projects' teams.

    :param project: The source project
    :type project: DataProject
    """
    # Load active teams for the source project that are not yet copied
    logger.debug("Team Sync: Processing new teams")
    for team in project.team_set.filter(status=TEAM_ACTIVE):

        # Iterate projects that use this project's teams
        for sharing_project in DataProject.objects.filter(teams_source=project):

            # Check if already created
            if Team.objects.filter(data_project=sharing_project, source=team).exists():
                logger.debug(f"Team Sync: Team/{team} already shared with DataProject/{sharing_project}")
                continue

            # Create the team
            shared_team = Team(
                source=team,
                data_project=sharing_project,
                team_leader=team.team_leader,
                status=TEAM_READY,
            )
            shared_team.save()

            # Iterate participants in the source team
            for participant in team.participant_set.all():

                # Create a new one
                shared_participant = Participant(
                    user=participant.user,
                    project=sharing_project,
                    team=shared_team,
                    team_wait_on_leader_email=participant.team_wait_on_leader_email,
                    team_wait_on_leader=participant.team_wait_on_leader,
                    team_pending=participant.team_pending,
                    team_approved=participant.team_approved,
                )
                shared_participant.save()

    # Load deactivated teams for the source project that have been copied
    logger.debug("Team Sync: Processing deactivated teams")
    for team in project.team_set.filter(status=TEAM_DEACTIVATED):

        # Iterate copied teams
        for shared_team in Team.objects.filter(source=team):

            # Set as deactivated
            shared_team.status = TEAM_DEACTIVATED
            shared_team.save()
