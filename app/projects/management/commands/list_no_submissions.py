import json
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from dbmi_client import fileservice

from projects.models import DataProject
from projects.models import Team, TEAM_ACTIVE, TEAM_DEACTIVATED
from projects.models import Participant
from projects.models import HostedFile
from projects.models import HostedFileDownload

from contact.views import email_send

import logging
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'List teams/participants that downloaded files for a project but did not provide submissions'

    def add_arguments(self, parser):
        # Positional arguments
        parser.add_argument('project_key', type=str)

        # Optional arguments
        parser.add_argument('-r', '--recipient', type=str, help='The recipient for operation report', )

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
            teams = Team.objects.filter(data_project=project)

            # Filter out teams without submissions
            teams_without_submissions = [t for t in teams if not t.get_submissions()]

            # Get all hosted files for the project
            hosted_files = HostedFile.objects.filter(project=project)

            # Track teams with no submissions but did download hosted files
            teams_with_access_and_no_submissions = []

            # Find teams with a user that downloaded any of the files for the project
            for team in teams_without_submissions:

                # Iterate participants
                for participant in team.participant_set.all():

                    # Find downloads
                    if HostedFileDownload.objects.filter(hosted_file__in=hosted_files, user=participant.user):

                        # Add them
                        teams_with_access_and_no_submissions.append(team)
                        break

            # Build report object
            report = {
                "total_teams_with_downloads_and_no_submissions": len(teams_with_access_and_no_submissions),
                "teams_with_downloads_and_no_submissions": [
                    {"team_leader": team.team_leader.email, "team_id": team.id}
                    for team in teams_with_access_and_no_submissions
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
            participants = Participant.objects.filter(project=project)

            # Filter out teams without submissions
            participants_without_submissions = [p for p in participants if not p.get_submissions()]

            # Get all hosted files for the project
            hosted_files = HostedFile.objects.filter(project=project)

            # Track teams with no submissions but did download hosted files
            participants_with_access_and_no_submissions = []

            # Find teams with a user that downloaded any of the files for the project
            for participant in participants_without_submissions:

                # Find downloads
                if HostedFileDownload.objects.filter(hosted_file__in=hosted_files, user=participant.user):

                    # Add them
                    participants_with_access_and_no_submissions.append(participant)

            # Build report object
            report = {
                "total_participants_with_downloads_and_no_submissions": len(participants_with_access_and_no_submissions),
                "participants_with_downloads_and_no_submissions": [
                    {"email": participant.user.email, "participant_id": participant.id}
                    for participant in participants_with_access_and_no_submissions
                ],
                "total_active_participants": len(participants),
            }

            # Output
            self.stdout.write(self.style.SUCCESS(json.dumps(report)))

            # Check for recipient
            if options['recipient']:

                # Send it
                self.email_report(options['project_key'], options['recipient'], json.dumps(report))
