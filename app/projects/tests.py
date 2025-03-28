import uuid
import io
from datetime import datetime, timezone, timedelta
from mock import patch
from zipfile import ZipFile
from urllib.parse import urlencode
import copy

from django.core import mail
from django.test import TestCase, RequestFactory, Client
from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.conf import settings
from django.http import HttpResponse
from dbmi_client.settings import dbmi_settings
from dbmisvc_test.request_response import RequestResponse, Method
from dbmisvc_test.responses import mock_authz_get_permission_response
from dbmisvc_test.responses import mock_authz_grant_registration_permission_response
from dbmisvc_test.responses import mock_fileservice_download_archivefile_response
from dbmisvc_test.responses import mock_fileservice_get_archivefile_response
from dbmisvc_test.responses import mock_fileservice_get_archivefiles_response
from dbmisvc_test.responses import mock_fileservice_create_archivefile_response
from dbmisvc_test.responses import mock_fileservice_archivefile_post_response
from dbmisvc_test.responses import mock_fileservice_uploaded_archivefile_response
from dbmisvc_test.responses import mock_s3_upload_response
from dbmisvc_test.responses import mock_fileservice_archivefile_download_response
from dbmisvc_test.responses import mock_fileservice_get_groups_response

from test.test_case import HypatioTestCase
from projects.models import DataProject
from projects.models import Participant
from projects.models import HostedFile
from projects.models import Team
from projects.models import ChallengeTask
from projects.models import TEAM_PENDING, TEAM_ACTIVE, TEAM_READY, TEAM_DEACTIVATED
from projects.models import HostedFileDownload
from projects.models import ChallengeTaskSubmission
from projects.models import AgreementForm
from projects.models import SignedAgreementForm

class FinalizeTeamTestCase(HypatioTestCase):

    # Set the URL pattern for this view.
    url_pattern = "projects:finalize_team"

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        # Create a project
        cls.project = DataProject.objects.create(
            name='Test Project',
            description='This is a test project',
            project_key='test_project',
            project_supervisors=cls.admin.email,
        )

        # Setup a team
        cls.team = Team.objects.create(
            data_project=cls.project,
            team_leader=cls.user,
        )
        cls.participant = Participant.objects.create(
            user=cls.user,
            project=cls.project,
            team=cls.team,
        )

        # Add a couple additional members
        cls.team_member_a = get_user_model().objects.create_user(
            email="team_member_a@email.com",
            username="team_member_a@email.com",
            first_name="Team",
            last_name="Member A",
        )
        cls.participant_a = Participant.objects.create(
            user=cls.team_member_a,
            project=cls.project,
            team=cls.team,
        )

        cls.team_member_b = get_user_model().objects.create_user(
            email="team_member_b@email.com",
            username="team_member_b@email.com",
            first_name="Team",
            last_name="Member B",
        )
        cls.participant_b = Participant.objects.create(
            user=cls.team_member_b,
            project=cls.project,
            team=cls.team,
        )

    def setUp(self):
        super().setUp()

        # Set the URL for the tests
        self.url = reverse(self.url_pattern)

        # Set the request response objects
        self.request_responses = [
            RequestResponse(
                "Successful request",
                [
                ],
                self.client,
                Method.POST,
                self.url,
                {
                    "project_key": self.project.project_key,
                    "team": self.user.email,
                },
                200,
                "text/html; charset=utf-8",
                True,
                True,
            ),
            RequestResponse(
                "Anonymous request",
                [],
                self.anonymous_client,
                Method.POST,
                self.url,
                {
                    "project_key": self.project.project_key,
                    "team": self.user.email,
                },
                302,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid project parameter key request",
                [
                ],
                self.client,
                Method.POST,
                self.url,
                {
                    "project-key": self.project.project_key,
                    "team": self.user.email,
                },
                400,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid project parameter value request",
                [
                ],
                self.client,
                Method.POST,
                self.url,
                {
                    "project_key": "not-a-project-key",
                    "team": self.user.email,
                },
                404,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid project parameter key request",
                [
                ],
                self.client,
                Method.POST,
                self.url,
                {
                    "project_key": self.project.project_key,
                    "team-leader-email": self.user.email,
                },
                400,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid team parameter value request",
                [
                ],
                self.client,
                Method.POST,
                self.url,
                {
                    "project_key": self.project.project_key,
                    "team": "some-other@email.com",
                },
                404,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Incorrect user request",
                [
                ],
                self.admin_client,
                Method.POST,
                self.url,
                {
                    "project_key": self.project.project_key,
                    "team": self.user.email,
                },
                403,
                "text/html; charset=utf-8",
            ),
        ]

    def test_finalize_team(self):

        # Get a successul request response
        request_response = next(iter(r for r in self.request_responses if r.successful))

        # Make the call
        request_response.call()

        # Fetch the team
        team = Team.objects.get(team_leader=self.user)

        # Make some assertions
        self.assertEqual(team.status, "Ready")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "DBMI Portal - Finalized Team")
        self.assertIn(self.admin.email, mail.outbox[0].recipients())


class ApproveTeamJoinTestCase(HypatioTestCase):

    # Set the URL pattern for this view.
    url_pattern = "projects:approve_team_join"

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        # Create a project
        cls.project = DataProject.objects.create(
            name='Test Project',
            description='This is a test project',
            project_key='test_project',
            project_supervisors=cls.admin.email,
        )

        # Setup a team
        cls.team = Team.objects.create(
            data_project=cls.project,
            team_leader=cls.user,
        )
        cls.participant = Participant.objects.create(
            user=cls.user,
            project=cls.project,
            team=cls.team,
        )

        # Add a couple additional members
        cls.team_member_a = get_user_model().objects.create_user(
            email="team_member_a@email.com",
            username="team_member_a@email.com",
            first_name="Team",
            last_name="Member A",
        )
        cls.participant_a = Participant.objects.create(
            user=cls.team_member_a,
            project=cls.project,
            team=cls.team,
        )

        cls.team_member_b = get_user_model().objects.create_user(
            email="team_member_b@email.com",
            username="team_member_b@email.com",
            first_name="Team",
            last_name="Member B",
        )
        cls.participant_b = Participant.objects.create(
            user=cls.team_member_b,
            project=cls.project,
        )

    def setUp(self):
        super().setUp()

        # Set the URL for the tests
        self.url = reverse(self.url_pattern)

        # Set the request response objects
        self.request_responses = [
            RequestResponse(
                "Successful request",
                [
                ],
                self.client,
                Method.POST,
                self.url,
                {
                    "project_key": self.project.project_key,
                    "participant": self.team_member_b.email,
                },
                200,
                "text/html; charset=utf-8",
                True,
                True,
            ),
            RequestResponse(
                "Anonymous request",
                [],
                self.anonymous_client,
                Method.POST,
                self.url,
                {
                    "project_key": self.project.project_key,
                    "participant": self.team_member_b.email,
                },
                302,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid project parameter key request",
                [
                ],
                self.client,
                Method.POST,
                self.url,
                {
                    "project-key": self.project.project_key,
                    "participant": self.team_member_b.email,
                },
                400,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid project parameter value request",
                [
                ],
                self.client,
                Method.POST,
                self.url,
                {
                    "project_key": "not-a-project-key",
                    "participant": self.team_member_b.email,
                },
                404,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid project parameter key request",
                [
                ],
                self.client,
                Method.POST,
                self.url,
                {
                    "project_key": self.project.project_key,
                    "participant-email": self.team_member_b.email,
                },
                400,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid team parameter value request",
                [
                ],
                self.client,
                Method.POST,
                self.url,
                {
                    "project_key": self.project.project_key,
                    "participant": "some-other@email.com",
                },
                404,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Incorrect user request",
                [
                ],
                self.admin_client,
                Method.POST,
                self.url,
                {
                    "project_key": self.project.project_key,
                    "participant": self.team_member_b.email,
                },
                403,
                "text/html; charset=utf-8",
            ),
        ]

    def test_approve_team_join(self):

        # Get a successul request response
        request_response = next(iter(r for r in self.request_responses if r.successful))

        # Make the call
        request_response.call()

        # Fetch the team
        team = Team.objects.get(team_leader=self.user)

        # Make assertions
        self.assertIn(self.participant_b, team.participant_set.all())


class RejectTeamJoinTestCase(HypatioTestCase):

    # Set the URL pattern for this view.
    url_pattern = "projects:reject_team_join"

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        # Create a project
        cls.project = DataProject.objects.create(
            name='Test Project',
            description='This is a test project',
            project_key='test_project',
            project_supervisors=cls.admin.email,
        )

        # Setup a team
        cls.team = Team.objects.create(
            data_project=cls.project,
            team_leader=cls.user,
        )
        cls.participant = Participant.objects.create(
            user=cls.user,
            project=cls.project,
            team=cls.team,
        )

        # Add a couple additional members
        cls.team_member_a = get_user_model().objects.create_user(
            email="team_member_a@email.com",
            username="team_member_a@email.com",
            first_name="Team",
            last_name="Member A",
        )
        cls.participant_a = Participant.objects.create(
            user=cls.team_member_a,
            project=cls.project,
            team=cls.team,
        )

        cls.team_member_b = get_user_model().objects.create_user(
            email="team_member_b@email.com",
            username="team_member_b@email.com",
            first_name="Team",
            last_name="Member B",
        )
        cls.participant_b = Participant.objects.create(
            user=cls.team_member_b,
            project=cls.project,
        )

    def setUp(self):
        super().setUp()

        # Set the URL for the tests
        self.url = reverse(self.url_pattern)

        # Set the request response objects
        self.request_responses = [
            RequestResponse(
                "Successful request",
                [
                ],
                self.client,
                Method.POST,
                self.url,
                {
                    "project_key": self.project.project_key,
                    "participant": self.team_member_b.email,
                },
                200,
                "text/html; charset=utf-8",
                True,
                True,
            ),
            RequestResponse(
                "Anonymous request",
                [],
                self.anonymous_client,
                Method.POST,
                self.url,
                {
                    "project_key": self.project.project_key,
                    "participant": self.team_member_b.email,
                },
                302,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid project parameter key request",
                [
                ],
                self.client,
                Method.POST,
                self.url,
                {
                    "project-key": self.project.project_key,
                    "participant": self.team_member_b.email,
                },
                400,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid project parameter value request",
                [
                ],
                self.client,
                Method.POST,
                self.url,
                {
                    "project_key": "not-a-project-key",
                    "participant": self.team_member_b.email,
                },
                404,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid project parameter key request",
                [
                ],
                self.client,
                Method.POST,
                self.url,
                {
                    "project_key": self.project.project_key,
                    "participant-email": self.team_member_b.email,
                },
                400,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid team parameter value request",
                [
                ],
                self.client,
                Method.POST,
                self.url,
                {
                    "project_key": self.project.project_key,
                    "participant": "some-other@email.com",
                },
                404,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Incorrect user request",
                [
                ],
                self.admin_client,
                Method.POST,
                self.url,
                {
                    "project_key": self.project.project_key,
                    "participant": self.team_member_b.email,
                },
                403,
                "text/html; charset=utf-8",
            ),
        ]

    def test_reject_team_join(self):

        # Get a successul request response
        request_response = next(iter(r for r in self.request_responses if r.successful))

        # Make the call
        request_response.call()

        # Fetch the team
        team = Team.objects.get(team_leader=self.user)

        # Make assertions
        self.assertNotIn(self.participant_b, team.participant_set.all())
        self.assertNotIn(self.participant_b, Participant.objects.all())


class LeaveTeamTestCase(HypatioTestCase):

    # Set the URL pattern for this view.
    url_pattern = "projects:leave_team"

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        # Create a project
        cls.project = DataProject.objects.create(
            name='Test Project',
            description='This is a test project',
            project_key='test_project',
            project_supervisors=cls.admin.email,
        )

        # Setup a team
        cls.team = Team.objects.create(
            data_project=cls.project,
            team_leader=cls.user,
        )
        cls.participant = Participant.objects.create(
            user=cls.user,
            project=cls.project,
            team=cls.team,
        )

        # Add a couple additional members
        cls.team_member_a = get_user_model().objects.create_user(
            email="team_member_a@email.com",
            username="team_member_a@email.com",
            first_name="Team",
            last_name="Member A",
        )
        cls.participant_a = Participant.objects.create(
            user=cls.team_member_a,
            project=cls.project,
            team=cls.team,
        )

        cls.team_member_b = get_user_model().objects.create_user(
            email="team_member_b@email.com",
            username="team_member_b@email.com",
            first_name="Team",
            last_name="Member B",
        )
        cls.participant_b = Participant.objects.create(
            user=cls.team_member_b,
            project=cls.project,
            team=cls.team,
        )

        # Setup a client for team member B
        cls.team_member_b_client = Client()
        cls.team_member_b.jwt = cls.test_authentication.get_jwt(
            first_name = cls.team_member_b.first_name,
            last_name = cls.team_member_b.last_name,
            email = cls.team_member_b.email,
        )

        # Login.
        cls.team_member_b_client.cookies['DBMI_JWT'] = cls.team_member_b.jwt
        cls.team_member_b_client.force_login(cls.team_member_b)

    def setUp(self):
        super().setUp()

        # Set the URL for the tests
        self.url = reverse(self.url_pattern)

        # Set the request response objects
        self.request_responses = [
            RequestResponse(
                "Successful request",
                [
                ],
                self.team_member_b_client,
                Method.POST,
                self.url,
                {
                    "project_key": self.project.project_key,
                },
                302,
                "text/html; charset=utf-8",
                True,
                True,
            ),
            RequestResponse(
                "Anonymous request",
                [],
                self.anonymous_client,
                Method.POST,
                self.url,
                {
                    "project_key": self.project.project_key,
                },
                302,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid project parameter key request",
                [
                ],
                self.team_member_b_client,
                Method.POST,
                self.url,
                {
                    "project-key": self.project.project_key,
                },
                400,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid project parameter value request",
                [
                ],
                self.team_member_b_client,
                Method.POST,
                self.url,
                {
                    "project_key": "not-a-project-key",
                },
                404,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid project parameter key request",
                [
                ],
                self.team_member_b_client,
                Method.POST,
                self.url,
                {
                    "project_key": self.project.project_key,
                },
                400,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Team leader request",
                [
                ],
                self.client,
                Method.POST,
                self.url,
                {
                    "project_key": self.project.project_key,
                },
                400,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Incorrect user request",
                [
                ],
                self.admin_client,
                Method.POST,
                self.url,
                {
                    "project_key": self.project.project_key,
                },
                404,
                "text/html; charset=utf-8",
            ),
        ]

    def test_leave_team(self):

        # Get a successul request response
        request_response = next(iter(r for r in self.request_responses if r.successful))

        # Make the call
        request_response.call()

        # Fetch the team
        team = Team.objects.get(team_leader=self.user)

        # Make assertions
        self.assertNotIn(self.participant_b, team.participant_set.all())


class JoinTeamTestCase(HypatioTestCase):

    # Set the URL pattern for this view.
    url_pattern = "projects:join_team"

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        # Create a project
        cls.project = DataProject.objects.create(
            name='Test Project',
            description='This is a test project',
            project_key='test_project',
            project_supervisors=cls.admin.email,
        )

        # Setup a team
        cls.team = Team.objects.create(
            data_project=cls.project,
            team_leader=cls.user,
        )
        cls.participant = Participant.objects.create(
            user=cls.user,
            project=cls.project,
            team=cls.team,
        )

        # Add a couple additional members
        cls.team_member_a = get_user_model().objects.create_user(
            email="team_member_a@email.com",
            username="team_member_a@email.com",
            first_name="Team",
            last_name="Member A",
        )
        cls.participant_a = Participant.objects.create(
            user=cls.team_member_a,
            project=cls.project,
            team=cls.team,
        )

        # Setup a client for team member A
        cls.team_member_a_client = Client()
        cls.team_member_a.jwt = cls.test_authentication.get_jwt(
            first_name = cls.team_member_a.first_name,
            last_name = cls.team_member_a.last_name,
            email = cls.team_member_a.email,
        )

        # Login.
        cls.team_member_a_client.cookies['DBMI_JWT'] = cls.team_member_a.jwt
        cls.team_member_a_client.force_login(cls.team_member_a)

        cls.team_member_b = get_user_model().objects.create_user(
            email="team_member_b@email.com",
            username="team_member_b@email.com",
            first_name="Team",
            last_name="Member B",
        )
        cls.participant_b = Participant.objects.create(
            user=cls.team_member_b,
            project=cls.project,
        )

        # Setup a client for team member B
        cls.team_member_b_client = Client()
        cls.team_member_b.jwt = cls.test_authentication.get_jwt(
            first_name = cls.team_member_b.first_name,
            last_name = cls.team_member_b.last_name,
            email = cls.team_member_b.email,
        )

        # Login.
        cls.team_member_b_client.cookies['DBMI_JWT'] = cls.team_member_b.jwt
        cls.team_member_b_client.force_login(cls.team_member_b)

    def setUp(self):
        super().setUp()

        # Set the URL for the tests
        self.url = reverse(self.url_pattern)

        # Set the request response objects
        self.request_responses = [
            RequestResponse(
                "Successful request",
                [
                    mock_authz_grant_registration_permission_response(self.team_member_b.jwt),
                ],
                self.team_member_b_client,
                Method.POST,
                self.url,
                {
                    "project_key": self.project.project_key,
                    "team_leader": self.user.email,
                },
                302,
                "text/html; charset=utf-8",
                True,
                True,
            ),
            RequestResponse(
                "Anonymous request",
                [],
                self.anonymous_client,
                Method.POST,
                self.url,
                {
                    "project_key": self.project.project_key,
                    "team_leader": self.user.email,
                },
                302,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid project parameter key request",
                [
                ],
                self.team_member_b_client,
                Method.POST,
                self.url,
                {
                    "project-key": self.project.project_key,
                    "team_leader": self.user.email,
                },
                400,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid project parameter value request",
                [
                ],
                self.team_member_b_client,
                Method.POST,
                self.url,
                {
                    "project_key": "not-a-project-key",
                    "team_leader": self.user.email,
                },
                404,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid project parameter key request",
                [
                ],
                self.team_member_b_client,
                Method.POST,
                self.url,
                {
                    "project-key": self.project.project_key,
                    "team_leader": self.user.email,
                },
                400,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Team leader request",
                [
                ],
                self.client,
                Method.POST,
                self.url,
                {
                    "project_key": self.project.project_key,
                    "team_leader": self.user.email,
                },
                400,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Existing team member request",
                [
                ],
                self.team_member_a_client,
                Method.POST,
                self.url,
                {
                    "project_key": self.project.project_key,
                    "team_leader": self.user.email,
                },
                400,
                "text/html; charset=utf-8",
            ),
        ]

    def test_join_team(self):

        # Get a successul request response
        request_response = next(iter(r for r in self.request_responses if r.successful))

        # Make the call
        request_response.call()

        # Fetch the team
        team = Team.objects.get(team_leader=self.user)

        # Update participant B
        self.participant_b.refresh_from_db()

        # Make assertions
        self.assertIn(self.participant_b, team.participant_set.all())
        self.assertTrue(self.participant_b.team_pending)

        # Check emails
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.user.email, mail.outbox[0].recipients())

    def test_join_team_before_created(self):

        # First delete the team
        self.team.delete()

        # Get a successul request response
        request_response = next(iter(r for r in self.request_responses if r.successful))

        # Make the call
        request_response.call()

        # Update participant B
        self.participant_b.refresh_from_db()

        # Make assertions
        self.assertEqual(Team.objects.count(), 0)
        self.assertEqual(self.participant_b.team_wait_on_leader, True)
        self.assertEqual(self.participant_b.team_wait_on_leader_email, self.user.email)

    def test_join_team_deactivated(self):

        # First set the team as deactivated
        self.team.status = TEAM_DEACTIVATED
        self.team.save()

        # Get a successul request response
        request_response = next(iter(r for r in self.request_responses if r.successful))

        # Make the call
        response = request_response.call(assert_all_mocks_called=False)

        # The return should be a redirect
        self.assertEqual(response.status_code, 302)
        self.assertFalse(self.participant_b.team)
        self.assertFalse(self.participant_b.team_pending)


class CreateTeamTestCase(HypatioTestCase):

    # Set the URL pattern for this view.
    url_pattern = "projects:create_team"

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        # Create a project
        cls.project = DataProject.objects.create(
            name='Test Project',
            description='This is a test project',
            project_key='test_project',
            project_supervisors=cls.admin.email,
        )

        # Setup a participant
        cls.participant = Participant.objects.create(
            user=cls.user,
            project=cls.project,
        )

        # Add a couple additional members
        cls.team_member_a = get_user_model().objects.create_user(
            email="team_member_a@email.com",
            username="team_member_a@email.com",
            first_name="Team",
            last_name="Member A",
        )
        cls.participant_a = Participant.objects.create(
            user=cls.team_member_a,
            project=cls.project,
        )

        # Setup a client for team member A
        cls.team_member_a_client = Client()
        cls.team_member_a.jwt = cls.test_authentication.get_jwt(
            first_name = cls.team_member_a.first_name,
            last_name = cls.team_member_a.last_name,
            email = cls.team_member_a.email,
        )

        # Login.
        cls.team_member_a_client.cookies['DBMI_JWT'] = cls.team_member_a.jwt
        cls.team_member_a_client.force_login(cls.team_member_a)

        cls.team_member_b = get_user_model().objects.create_user(
            email="team_member_b@email.com",
            username="team_member_b@email.com",
            first_name="Team",
            last_name="Member B",
        )
        cls.participant_b = Participant.objects.create(
            user=cls.team_member_b,
            project=cls.project,
        )

        # Setup a client for team member B
        cls.team_member_b_client = Client()
        cls.team_member_b.jwt = cls.test_authentication.get_jwt(
            first_name = cls.team_member_b.first_name,
            last_name = cls.team_member_b.last_name,
            email = cls.team_member_b.email,
        )

        # Login.
        cls.team_member_b_client.cookies['DBMI_JWT'] = cls.team_member_b.jwt
        cls.team_member_b_client.force_login(cls.team_member_b)

    def setUp(self):
        super().setUp()

        # Set the URL for the tests
        self.url = reverse(self.url_pattern)

        # Set the request response objects
        self.request_responses = [
            RequestResponse(
                "Successful request",
                [
                ],
                self.client,
                Method.POST,
                self.url,
                {
                    "project_key": self.project.project_key,
                },
                302,
                "text/html; charset=utf-8",
                True,
                True,
            ),
            RequestResponse(
                "Anonymous request",
                [],
                self.anonymous_client,
                Method.POST,
                self.url,
                {
                    "project_key": self.project.project_key,
                },
                302,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid project parameter key request",
                [
                ],
                self.client,
                Method.POST,
                self.url,
                {
                    "project-key": self.project.project_key,
                },
                400,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid project parameter value request",
                [
                ],
                self.client,
                Method.POST,
                self.url,
                {
                    "project_key": "not-a-project-key",
                },
                404,
                "text/html; charset=utf-8",
            ),
        ]

    def test_create_team(self):

        # Get a successul request response
        request_response = next(iter(r for r in self.request_responses if r.successful))

        # Make the call
        request_response.call()

        # Make assertions
        self.assertEqual(Team.objects.count(), 1)
        self.assertEqual(Team.objects.first().team_leader, self.user)
        self.assertEqual(Team.objects.first().participant_set.count(), 1)

    def test_create_team_waiting(self):

        # Setup participants to be waiting
        self.participant_a.team_wait_on_leader = True
        self.participant_a.team_wait_on_leader_email = self.user.email
        self.participant_a.save()

        # Get a successul request response
        request_response = next(iter(r for r in self.request_responses if r.successful))

        # Make the call
        request_response.call()

        # Update participant
        self.participant_a.refresh_from_db()

        # Make assertions
        self.assertEqual(Team.objects.count(), 1)
        self.assertTrue(Team.objects.get(team_leader=self.user))
        self.assertEqual(Team.objects.get(team_leader=self.user).participant_set.count(), 2)
        self.assertEqual(self.participant_a.team, Team.objects.get(team_leader=self.user))
        self.assertTrue(self.participant_a.team_pending)


class DownloadDatasetTestCase(HypatioTestCase):

    # Set the URL pattern for this view.
    url_pattern = "projects:download_dataset"

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        # Create a project
        cls.project = DataProject.objects.create(
            name='Test Project',
            description='This is a test project',
            project_key='test_project',
            project_supervisors=cls.admin.email,
        )

        # Setup a participant
        cls.participant = Participant.objects.create(
            user=cls.user,
            project=cls.project,
        )

        # Add a couple additional members
        cls.team_member_a = get_user_model().objects.create_user(
            email="team_member_a@email.com",
            username="team_member_a@email.com",
            first_name="Team",
            last_name="Member A",
        )
        cls.participant_a = Participant.objects.create(
            user=cls.team_member_a,
            project=cls.project,
        )

        # Setup a client for team member A
        cls.team_member_a_client = Client()
        cls.team_member_a.jwt = cls.test_authentication.get_jwt(
            first_name = cls.team_member_a.first_name,
            last_name = cls.team_member_a.last_name,
            email = cls.team_member_a.email,
        )

        # Login.
        cls.team_member_a_client.cookies['DBMI_JWT'] = cls.team_member_a.jwt
        cls.team_member_a_client.force_login(cls.team_member_a)

        cls.team_member_b = get_user_model().objects.create_user(
            email="team_member_b@email.com",
            username="team_member_b@email.com",
            first_name="Team",
            last_name="Member B",
        )
        cls.participant_b = Participant.objects.create(
            user=cls.team_member_b,
            project=cls.project,
        )

        # Setup a client for team member B
        cls.team_member_b_client = Client()
        cls.team_member_b.jwt = cls.test_authentication.get_jwt(
            first_name = cls.team_member_b.first_name,
            last_name = cls.team_member_b.last_name,
            email = cls.team_member_b.email,
        )

        # Login.
        cls.team_member_b_client.cookies['DBMI_JWT'] = cls.team_member_b.jwt
        cls.team_member_b_client.force_login(cls.team_member_b)

        # Setup a hosted file
        cls.hosted_file = HostedFile.objects.create(
            project=cls.project,
            long_name="A test data set",
            file_name="test_data_set.zip",
            file_location=f"s3://{settings.S3_BUCKET}/{cls.project.project_key}",
            enabled=True,
        )
        cls.file_url = f"https://{settings.S3_BUCKET}.s3.amazonaws.com/{cls.project.project_key}/{cls.hosted_file.file_name}"

        # Set the downloaded file content
        cls.dataset_contents = "This is a test submission's file contents in a zip file"
        zip_buffer = io.BytesIO()
        with ZipFile(zip_buffer, "a") as z:
            z.writestr("submission_file.txt", cls.dataset_contents)

        # Save it
        cls.dataset = zip_buffer.getvalue()

    def setUp(self):
        super().setUp()

        # Set the URL for the tests
        self.url = reverse(self.url_pattern)

        # Set the request response objects
        self.request_responses = [
            RequestResponse(
                "Successful request",
                [
                    mock_authz_get_permission_response(self.user.jwt, f"Hypatio.{self.project.project_key}", "VIEW"),
                ],
                self.client,
                Method.GET,
                self.url,
                {
                    "file_uuid": self.hosted_file.uuid,
                },
                302,
                "text/html; charset=utf-8",
                True,
                True,
            ),
            RequestResponse(
                "Anonymous request",
                [],
                self.anonymous_client,
                Method.GET,
                self.url,
                {
                    "file_uuid": self.hosted_file.uuid,
                },
                302,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid file parameter key request",
                [
                ],
                self.client,
                Method.GET,
                self.url,
                {
                    "file-uuid": self.hosted_file.uuid,
                },
                400,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid file parameter value request",
                [
                    mock_authz_get_permission_response(self.user.jwt, f"Hypatio.{self.project.project_key}", "VIEW"),
                ],
                self.client,
                Method.GET,
                self.url,
                {
                    "file_uuid": str(uuid.uuid4()),
                },
                404,
                "text/html; charset=utf-8",
            ),
        ]

    def test_status_code(self):

        # Iterate request/response objects
        for request_response in self.request_responses:
            with self.subTest(msg=request_response.name, request_response=request_response):

                # Setup a mock on the generate presigned URL method
                with patch("botocore.signers.generate_presigned_url") as mock_boto:

                    # Set a return value
                    mock_boto.return_value = self.file_url

                    # Call it
                    response = request_response.call()

                    # Make assertions
                    self.assertEqual(response.status_code, request_response.status_code)

    def test_content_type(self):

        # Iterate request/response objects
        for request_response in self.request_responses:
            with self.subTest(msg=request_response.name, request_response=request_response):

                # Setup a mock on the generate presigned URL method
                with patch("botocore.signers.generate_presigned_url") as mock_boto:

                    # Set a return value
                    mock_boto.return_value = self.file_url

                    # Call it
                    response = request_response.call()

                    # Make assertions
                    self.assertEqual(response["Content-Type"], request_response.content_type)

    def test_download_dataset(self):

        # Get a successul request response
        request_response = next(iter(r for r in self.request_responses if r.successful))

        # Setup a mock on the generate presigned URL method
        with patch("botocore.signers.generate_presigned_url") as mock_boto:

            # Set a return value
            mock_boto.return_value = self.file_url

            # Make the call
            response = request_response.call()

            # Make assertsions
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.headers["Location"], self.file_url)

            # Ensure a download log was created
            self.assertTrue(HostedFileDownload.objects.get(user=self.user, hosted_file=self.hosted_file))

    def test_download_dataset_disabled(self):

        # Set the dataset as disabled
        self.hosted_file.enabled = False
        self.hosted_file.save()

        # Get a successul request response
        request_response = next(iter(r for r in self.request_responses if r.successful))

        # Make the call
        response = request_response.call(assert_all_mocks_called=False)

        # Make assertsions
        self.assertEqual(response.status_code, 403)

        # Ensure a download log was not created
        self.assertEqual(HostedFileDownload.objects.count(), 0)

    def test_download_dataset_date_closed(self):

        # Set the dataset as True but set a past closed date
        self.hosted_file.enabled = True
        self.hosted_file.closed_time = datetime.now(timezone.utc) - timedelta(days=1)
        self.hosted_file.save()

        # Get a successul request response
        request_response = next(iter(r for r in self.request_responses if r.successful))

        # Make the call
        response = request_response.call(assert_all_mocks_called=False)

        # Make assertsions
        self.assertEqual(response.status_code, 403)

        # Ensure a download log was not created
        self.assertEqual(HostedFileDownload.objects.count(), 0)

    def test_download_dataset_date_not_opened(self):

        # Set the dataset as True but set a future opened date
        self.hosted_file.enabled = True
        self.hosted_file.opened_time = datetime.now(timezone.utc) + timedelta(days=1)
        self.hosted_file.save()

        # Get a successul request response
        request_response = next(iter(r for r in self.request_responses if r.successful))

        # Make the call
        response = request_response.call(assert_all_mocks_called=False)

        # Make assertsions
        self.assertEqual(response.status_code, 403)

        # Ensure a download log was not created
        self.assertEqual(HostedFileDownload.objects.count(), 0)


class UploadChallengeTaskSubmissionFileTestCase(HypatioTestCase):

    # Set the URL pattern for this view.
    url_pattern = "projects:upload_challengetasksubmission_file"

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        # Create a project
        cls.project = DataProject.objects.create(
            name='Test Project',
            description='This is a test project',
            project_key='test_project',
        )

        # Setup a team
        cls.team = Team.objects.create(
            data_project=cls.project,
            team_leader=cls.user,
        )
        cls.participant = Participant.objects.create(
            user=cls.user,
            project=cls.project,
            team=cls.team,
        )

        # Setup a challenge task
        cls.challenge_task = ChallengeTask.objects.create(
            title="Test Task",
            description="This is a test task",
            data_project=cls.project,
            enabled=True,
        )

        # Set an ArchiveFile UUID
        cls.archivefile_uuid = str(uuid.uuid4())

    def setUp(self):
        super().setUp()

        # Set the URL for the tests
        self.url = reverse(self.url_pattern)

        # Set the request response objects
        self.request_responses = [
            RequestResponse(
                "Successful request",
                [
                    mock_authz_get_permission_response(self.user.jwt, f"Hypatio.{self.project.project_key}", "VIEW"),
                    mock_fileservice_get_groups_response(dbmi_settings.FILESERVICE_TOKEN, [{"name": f'{settings.FILESERVICE_GROUP}__UPLOADERS'}]),
                    mock_fileservice_create_archivefile_response(dbmi_settings.FILESERVICE_TOKEN, self.archivefile_uuid),
                    mock_fileservice_archivefile_post_response(dbmi_settings.FILESERVICE_TOKEN, settings.FILESERVICE_AWS_BUCKET, "submission.zip"),
                ],
                self.client,
                Method.POST,
                self.url,
                {
                    "project_key": self.project.project_key,
                    "filename": "test-challengetasksubmission-file.zip",
                    "task_id": self.challenge_task.id,
                },
                200,
                "application/json",
                True,
                True,
            ),
            RequestResponse(
                "Anonymous request",
                [],
                self.anonymous_client,
                Method.POST,
                self.url,
                {
                    "project_key": self.project.project_key,
                    "filename": "test-challengetasksubmission-file.zip",
                    "task_id": self.challenge_task.id,
                },
                302,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid project parameter key request",
                [
                ],
                self.client,
                Method.POST,
                self.url,
                {
                    "project-key": self.project.project_key,
                    "filename": "test-challengetasksubmission-file.zip",
                    "task_id": self.challenge_task.id,
                },
                400,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid project parameter value request",
                [
                    mock_authz_get_permission_response(self.user.jwt, f"Hypatio.{self.project.project_key}", "VIEW"),
                ],
                self.client,
                Method.POST,
                self.url,
                {
                    "project_key": "not-a-project-key",
                    "filename": "test-challengetasksubmission-file.zip",
                    "task_id": self.challenge_task.id,
                },
                404,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid task parameter key request",
                [
                ],
                self.client,
                Method.POST,
                self.url,
                {
                    "project_key": self.project.project_key,
                    "filename": "test-challengetasksubmission-file.zip",
                    "task-id": self.challenge_task.id,
                },
                400,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid task parameter value request",
                [
                    mock_authz_get_permission_response(self.user.jwt, f"Hypatio.{self.project.project_key}", "VIEW"),
                ],
                self.client,
                Method.POST,
                self.url,
                {
                    "project_key": self.project.project_key,
                    "filename": "test-challengetasksubmission-file.zip",
                    "task_id": 9999,
                },
                400,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Successful PATCH request",
                [
                    mock_authz_get_permission_response(self.user.jwt, f"Hypatio.{self.project.project_key}", "VIEW"),
                    mock_fileservice_uploaded_archivefile_response(dbmi_settings.FILESERVICE_TOKEN, self.archivefile_uuid),
                ],
                self.client,
                Method.PATCH,
                self.url,
                urlencode({
                    "project_key": self.project.project_key,
                    "task_id": self.challenge_task.id,
                    "csrfmiddlewaretoken": "abc123",
                    "uuid": self.archivefile_uuid,
                    "location": 10,
                }),
                200,
                "text/html; charset=utf-8",
                True,
                True,
            ),
            RequestResponse(
                "Anonymous request",
                [],
                self.anonymous_client,
                Method.PATCH,
                self.url,
                urlencode({
                    "project_key": self.project.project_key,
                    "task_id": self.challenge_task.id,
                    "csrfmiddlewaretoken": "abc123",
                    "uuid": self.archivefile_uuid,
                    "location": 10,
                }),
                302,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid ArchiveFile UUID parameter key request",
                [
                ],
                self.client,
                Method.PATCH,
                self.url,
                urlencode({
                    "project_key": self.project.project_key,
                    "task_id": self.challenge_task.id,
                    "csrfmiddlewaretoken": "abc123",
                    "archivefile-uuid": self.archivefile_uuid,
                    "location": 10,
                }),
                400,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid ArchiveFile UUID parameter value request",
                [
                    mock_authz_get_permission_response(self.user.jwt, f"Hypatio.{self.project.project_key}", "VIEW"),
                ],
                self.client,
                Method.PATCH,
                self.url,
                urlencode({
                    "project_key": self.project.project_key,
                    "task_id": self.challenge_task.id,
                    "csrfmiddlewaretoken": "abc123",
                    "uuid": str(uuid.uuid4()),
                    "location": 10,
                }),
                200, # TODO: This should be a 404
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid location parameter key request",
                [
                ],
                self.client,
                Method.PATCH,
                self.url,
                urlencode({
                    "project_key": self.project.project_key,
                    "task_id": self.challenge_task.id,
                    "csrfmiddlewaretoken": "abc123",
                    "uuid": str(uuid.uuid4()),
                    "location-id": 10,
                }),
                400,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid location parameter value request",
                [
                    mock_authz_get_permission_response(self.user.jwt, f"Hypatio.{self.project.project_key}", "VIEW"),
                ],
                self.client,
                Method.PATCH,
                self.url,
                urlencode({
                    "project_key": self.project.project_key,
                    "task_id": self.challenge_task.id,
                    "csrfmiddlewaretoken": "abc123",
                    "uuid": str(uuid.uuid4()),
                    "location": 9999,
                }),
                200, # TODO: This should be a 404
                "text/html; charset=utf-8",
            ),
        ]



class SubmitUserPermissionRequestTestCase(HypatioTestCase):

    # Set the URL pattern for this view.
    url_pattern = "projects:submit_user_permission_request"

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        # Create a project
        cls.project = DataProject.objects.create(
            name='Test Project',
            description='This is a test project',
            project_key='test_project',
        )

    def setUp(self):
        super().setUp()

        # Set the URL for the tests
        self.url = reverse(self.url_pattern)

        # Set the request response objects
        self.request_responses = [
            RequestResponse(
                "Successful request",
                [
                ],
                self.client,
                Method.POST,
                self.url,
                {
                    "project_key": self.project.project_key,
                },
                201,
                "text/html; charset=utf-8",
                True,
                True,
            ),
            RequestResponse(
                "Anonymous request",
                [],
                self.anonymous_client,
                Method.POST,
                self.url,
                {
                    "project_key": self.project.project_key,
                    "registration_status": "open",
                },
                302,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid project parameter key request",
                [
                ],
                self.client,
                Method.POST,
                self.url,
                {
                    "project-key": self.project.project_key,
                },
                400,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid project parameter value request",
                [
                ],
                self.client,
                Method.POST,
                self.url,
                {
                    "project_key": "not-a-project-key",
                },
                404,
                "text/html; charset=utf-8",
            ),
        ]


class DeleteChallengeTaskSubmissionTestCase(HypatioTestCase):

    # Set the URL pattern for this view.
    url_pattern = "projects:delete_challengetasksubmission"

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        # Create a project
        cls.project = DataProject.objects.create(
            name='Test Project',
            description='This is a test project',
            project_key='test_project',
            has_teams=True,
        )

        # Setup a team
        cls.team = Team.objects.create(
            data_project=cls.project,
            team_leader=cls.user,
        )
        cls.participant = Participant.objects.create(
            user=cls.user,
            project=cls.project,
            team=cls.team,
        )

        # Add an additional additional members
        cls.team_member_a = get_user_model().objects.create_user(
            email="team_member_a@email.com",
            username="team_member_a@email.com",
            first_name="Team",
            last_name="Member A",
        )
        cls.team_member_a.jwt = cls.test_authentication.get_jwt(
            first_name = cls.team_member_a.first_name,
            last_name = cls.team_member_a.last_name,
            email = cls.team_member_a.email,
        )
        cls.team_member_a_client = Client()
        cls.team_member_a_client.cookies['DBMI_JWT'] = cls.team_member_a.jwt
        cls.team_member_a_client.force_login(cls.team_member_a)

        cls.participant_a = Participant.objects.create(
            user=cls.team_member_a,
            project=cls.project,
            team=cls.team,
        )

        cls.team_member_b = get_user_model().objects.create_user(
            email="team_member_b@email.com",
            username="team_member_b@email.com",
            first_name="Team",
            last_name="Member B",
        )
        cls.team_member_b.jwt = cls.test_authentication.get_jwt(
            first_name = cls.team_member_b.first_name,
            last_name = cls.team_member_b.last_name,
            email = cls.team_member_b.email,
        )
        cls.team_member_b_client = Client()
        cls.team_member_b_client.cookies['DBMI_JWT'] = cls.team_member_b.jwt
        cls.team_member_b_client.force_login(cls.team_member_b)

        cls.participant_b = Participant.objects.create(
            user=cls.team_member_b,
            project=cls.project,
            team=cls.team,
        )

        # Setup a challenge task
        cls.challenge_task = ChallengeTask.objects.create(
            title="Test Task",
            description="This is a test task",
            data_project=cls.project,
            enabled=True,
        )

        # Set a UUID for the challenge task submission
        cls.submission_uuid = uuid.uuid4()

        # Create a challenge task submission
        cls.challenge_task_submission = ChallengeTaskSubmission.objects.create(
            challenge_task=cls.challenge_task,
            participant=cls.participant_a,
            uuid=cls.submission_uuid,
        )

    def setUp(self):
        super().setUp()

        # Set the URL for the tests
        self.url = reverse(self.url_pattern)

        # Set the request response objects
        self.request_responses = [
            RequestResponse(
                "Owner request",
                [
                    mock_authz_get_permission_response(self.team_member_a.jwt, f"Hypatio.{self.project.project_key}", "VIEW"),
                ],
                self.team_member_a_client,
                Method.POST,
                self.url,
                {
                    "submission_uuid": self.challenge_task_submission.uuid,
                },
                200,
                "text/html; charset=utf-8",
                True,
                True,
                handler=lambda response: self.assertEqual(len(mail.outbox), 1),
            ),
            RequestResponse(
                "Anonymous request",
                [],
                self.anonymous_client,
                Method.POST,
                self.url,
                {
                    "submission_uuid": self.challenge_task_submission.uuid,
                },
                302,
                "text/html; charset=utf-8",
                handler=lambda response: self.assertEqual(len(mail.outbox), 0),
            ),
            RequestResponse(
                "Invalid submission UUID parameter key request",
                [
                ],
                self.team_member_a_client,
                Method.POST,
                self.url,
                {
                    "submission-uuid": self.challenge_task_submission.uuid,
                },
                400,
                "text/html; charset=utf-8",
                handler=lambda response: self.assertEqual(len(mail.outbox), 0),
            ),
            RequestResponse(
                "Invalid submission UUID parameter value request",
                [
                    mock_authz_get_permission_response(self.team_member_a.jwt, f"Hypatio.{self.project.project_key}", "VIEW"),
                ],
                self.team_member_a_client,
                Method.POST,
                self.url,
                {
                    "submission_uuid": str(uuid.uuid4()),
                },
                404,
                "text/html; charset=utf-8",
                handler=lambda response: self.assertEqual(len(mail.outbox), 0),
            ),
            RequestResponse(
                "Non-owner request",
                [
                    mock_authz_get_permission_response(self.team_member_b.jwt, f"Hypatio.{self.project.project_key}", "VIEW"),
                ],
                self.team_member_b_client,
                Method.POST,
                self.url,
                {
                    "submission_uuid": self.challenge_task_submission.uuid,
                },
                403,
                "text/html; charset=utf-8",
                handler=lambda response: self.assertEqual(len(mail.outbox), 0),
            ),
            RequestResponse(
                "Team leader request",
                [
                    mock_authz_get_permission_response(self.user.jwt, f"Hypatio.{self.project.project_key}", "VIEW"),
                ],
                self.client,
                Method.POST,
                self.url,
                {
                    "submission_uuid": self.challenge_task_submission.uuid,
                },
                200,
                "text/html; charset=utf-8",
                True,
                True,
                handler=lambda response: self.assertEqual(len(mail.outbox), 1),
            ),
        ]

    def test_delete_challengetasksubmission_participant_permission(self):

        # Get a successful request response
        request_response = copy.deepcopy(next(iter(r for r in self.request_responses if r.successful and r.client == self.client)))

        # Remove the mocked AuthZ response
        request_response.mocks = [mock_authz_get_permission_response(self.user.jwt, f"Hypatio.{self.project.project_key}", None)]

        # Add the permission to the Participant object
        self.participant.permission = "VIEW"
        self.participant.save()

        # Run it
        request_response.call()

        # Make assertions
        self.assertTrue(ChallengeTaskSubmission.objects.get(uuid=self.challenge_task_submission.uuid).deleted)

    def test_delete_challengetasksubmission(self):

        # Get a successful request response
        request_response = next(iter(r for r in self.request_responses if r.successful))

        # Run it
        request_response.call()

        # Make assertions
        self.assertTrue(ChallengeTaskSubmission.objects.get(uuid=self.challenge_task_submission.uuid).deleted)


class SubmitUserPermissionRequestTestCase(HypatioTestCase):

    # Set the URL pattern for this view.
    url_pattern = "projects:submit_user_permission_request"

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        # Create a project
        cls.project = DataProject.objects.create(
            name='Test Project',
            description='This is a test project',
            project_key='test_project',
        )

    def setUp(self):
        super().setUp()

        # Set the URL for the tests
        self.url = reverse(self.url_pattern)

        # Set the request response objects
        self.request_responses = [
            RequestResponse(
                "Successful request",
                [
                ],
                self.client,
                Method.POST,
                self.url,
                {
                    "project_key": self.project.project_key,
                },
                201,
                "text/html; charset=utf-8",
                True,
                True,
            ),
            RequestResponse(
                "Anonymous request",
                [],
                self.anonymous_client,
                Method.POST,
                self.url,
                {
                    "project_key": self.project.project_key,
                    "registration_status": "open",
                },
                302,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid project parameter key request",
                [
                ],
                self.client,
                Method.POST,
                self.url,
                {
                    "project-key": self.project.project_key,
                },
                400,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid project parameter value request",
                [
                ],
                self.client,
                Method.POST,
                self.url,
                {
                    "project_key": "not-a-project-key",
                },
                404,
                "text/html; charset=utf-8",
            ),
        ]


class SaveSignedAgreementFormTestCase(HypatioTestCase):

    # Set the URL pattern for this view.
    url_pattern = "projects:save_signed_agreement_form"

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        # Create a project
        cls.project = DataProject.objects.create(
            name='Test Project',
            description='This is a test project',
            project_key='test_project',
        )

        # Create an agreement form
        cls.agreement_form = AgreementForm.objects.create(
            name='Test Agreement Form',
            short_name='test_agreement_form',
            form_file_path="agreementforms/4ce-dua.html",
        )

        # Add the agreement form to the project
        cls.project.agreement_forms.add(cls.agreement_form)
        cls.project.save()

    def setUp(self):
        super().setUp()

        # Set the URL for the tests
        self.url = reverse(self.url_pattern)

        # Set the request response objects
        self.request_responses = [
            RequestResponse(
                "Successful request",
                [
                ],
                self.client,
                Method.POST,
                self.url,
                {
                    "project_key": self.project.project_key,
                    "agreement_form_id": self.agreement_form.id,
                    "agreement_text": "I agree to the terms of this agreement",
                    "key1": "value1",
                    "key2": "value2",
                    "key3": "value3",
                },
                200,
                "text/html; charset=utf-8",
                True,
                True,
            ),
            RequestResponse(
                "Anonymous request",
                [
                ],
                self.anonymous_client,
                Method.POST,
                self.url,
                {
                    "project_key": self.project.project_key,
                    "agreement_form_id": self.agreement_form.id,
                    "agreement_text": "I agree to the terms of this agreement",
                    "key1": "value1",
                    "key2": "value2",
                    "key3": "value3",
                },
                302,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Incorrect project parameter key request",
                [
                ],
                self.client,
                Method.POST,
                self.url,
                {
                    "project": self.project.project_key,
                    "agreement_form_id": self.agreement_form.id,
                    "agreement_text": "I agree to the terms of this agreement",
                    "key1": "value1",
                    "key2": "value2",
                    "key3": "value3",
                },
                400,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Incorrect project parameter value request",
                [
                    mock_authz_get_permission_response(self.user.jwt, f"Hypatio.{self.project.project_key}", "VIEW"),
                ],
                self.client,
                Method.POST,
                self.url,
                {
                    "project_key": "not-a-project-key",
                    "agreement_form_id": self.agreement_form.id,
                    "agreement_text": "I agree to the terms of this agreement",
                    "key1": "value1",
                    "key2": "value2",
                    "key3": "value3",
                },
                404,
                "text/html; charset=utf-8",
            ),
        ]

    def test_save_signed_agreement_form(self):

        # Get a successful request response
        request_response = next(iter(r for r in self.request_responses if r.successful))

        # Run it
        request_response.call()

        # Make assertions
        self.assertEqual(SignedAgreementForm.objects.count(), 1)
        self.assertEqual(SignedAgreementForm.objects.first().fields.get("key1"), "value1")

    def test_save_signed_agreement_form_template(self):

        # Add a template to the AgreementForm
        self.agreement_form.template = "agreementforms/hms-dbmi-portal-pdf-template.html"
        self.agreement_form.save()

        # Get a successful request response
        request_response = next(iter(r for r in self.request_responses if r.successful))

        # Run it
        with patch("projects.api.render_pdf") as mock_render_pdf:
            mock_render_pdf.return_value = HttpResponse(content=b"Test PDF")

            # Setup a mock on the S3 copy object operation
            with patch("botocore.client.BaseClient._make_api_call"):

                # Run it
                request_response.call()

        # Make assertions
        self.assertEqual(SignedAgreementForm.objects.count(), 1)
        self.assertEqual(SignedAgreementForm.objects.first().fields.get("key1"), "value1")
