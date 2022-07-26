import json

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from projects.models import DataProject
from projects.models import Team, TEAM_ACTIVE, TEAM_DEACTIVATED
from projects.models import Participant
from contact.views import email_send

import logging
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Revoke access for individuals/teams without submissions'

    def add_arguments(self, parser):
        # Positional arguments
        parser.add_argument('project_key', type=str)

        # Optional arguments
        parser.add_argument('-r', '--recipient', type=str, help='The recipient for operation report', )
        parser.add_argument('-c', '--commit', action='store_true', help='Commit revocations for participants/teams', )

    def email_report(self, project_key, recipient, report, *args, **options):
        """
        Sends a report of the results of the operation.
        """
        # Set context
        context={
            "operation": self.help,
            "project": project_key,
            "message": report,
        }

        # Send it out.
        success = email_send(
            subject=f'DBMI Portal - Operation Report',
            recipients=[recipient],
            email_template='email_operation_report',
            extra=context
        )
        if success:
            self.stdout.write(self.style.SUCCESS(f"Report sent to: {recipient}"))
        else:
            self.stdout.write(self.style.ERROR(f"Report failed to send to: {recipient}"))


    def handle(self, *args, **options):

        # Ensure it exists
        if not DataProject.objects.filter(project_key=options['project_key']).exists():
            raise CommandError(f'Project with key "{options["project_key"]}" does not exist')

        # Get the objects
        project = DataProject.objects.get(project_key=options['project_key'])

        # Determine if a team-based challenge or not
        if project.has_teams:

            # Fetch teams
            teams = Team.objects.filter(data_project=project, status=TEAM_ACTIVE)

            # Filter out teams without submissions
            teams_without_submissions = [t for t in teams if not t.get_submissions()]

            # Iterate the list
            for team in teams_without_submissions:

                # Check if only listing
                if options['commit']:

                    # Revoke access for the team
                    team.status = TEAM_DEACTIVATED
                    team.save()

            # Build report object
            report = {
                "total_revoked_teams": len(teams_without_submissions),
                "revoked_teams": [
                    {"team_leader": team.team_leader.email, "team_id": team.id}
                    for team in teams_without_submissions
                ],
                "total_active_teams": len(teams),
            }

            # Output
            self.stdout.write(self.style.SUCCESS(json.dumps(report)))

            # Check for recipient
            if options['recipient']:

                # Send it
                self.email_report(options['project_key'], options['recipient'], json.dumps(report))

        else:

            # Get all participants
            participants = Participant.objects.filter(project=project, permission="VIEW")

            # Filter out teams without submissions
            participants_without_submissions = [p for p in participants if not p.get_submissions()]

            # Get all participants
            for participant in participants_without_submissions:

                # Check if only listing
                if options['commit']:

                    # Revoke access for the participant
                    participant.permission = None
                    participant.save()

            # Build report object
            report = {
                "total_revoked_participants": len(participants_without_submissions),
                "revoked_participants": [
                    {"email": participant.user.email, "participant_id": participant.id}
                    for participant in participants_without_submissions
                ],
                "total_active_participants": len(participants),
            }

            # Output
            self.stdout.write(self.style.SUCCESS(json.dumps(report)))

            # Check for recipient
            if options['recipient']:

                # Send it
                self.email_report(options['project_key'], options['recipient'], json.dumps(report))
