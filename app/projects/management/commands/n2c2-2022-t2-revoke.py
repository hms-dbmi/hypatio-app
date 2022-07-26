import json

from django.conf import settings
from django.core.management.base import BaseCommand

from projects.models import DataProject
from projects.models import Team, TEAM_ACTIVE, TEAM_DEACTIVATED
from contact.views import email_send

import logging
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Revoke access for teams that have not submitted for any subtasks'

    def add_arguments(self, parser):

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

        # Get the objects
        project = DataProject.objects.get(project_key="n2c2-2022-t2")

        # Collect teams without submissions
        teams_without_submissions = []

        # Fetch teams
        teams = Team.objects.filter(data_project=project, status=TEAM_ACTIVE)

        # Iterate teams
        for team in teams:

            # Get all sub teams
            sub_teams = Team.objects.filter(source=team)

            # Check if any have submissions
            has_submissions = next((t for t in sub_teams if t.get_submissions()), None)

            # Add to the list if nothing
            if not has_submissions:
                teams_without_submissions.append(team)

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
            self.email_report("n2c2-2022-t2", options['recipient'], json.dumps(report))
