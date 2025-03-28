import re
import string
import random
import uuid
import io
from datetime import datetime, timezone
from mock import patch
from zipfile import ZipFile

from django.core import mail
from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from dbmi_client.settings import dbmi_settings
import responses
from urllib.parse import urlparse, quote_plus
from dbmisvc_test.request_response import RequestResponse, Method
from dbmisvc_test.responses import mock_fileservice_download_archivefile_response
from dbmisvc_test.responses import mock_fileservice_get_archivefile_response
from dbmisvc_test.responses import mock_fileservice_get_archivefiles_response
from dbmisvc_test.responses import mock_fileservice_create_archivefile_response
from dbmisvc_test.responses import mock_fileservice_archivefile_post_response
from dbmisvc_test.responses import mock_fileservice_uploaded_archivefile_response
from dbmisvc_test.responses import mock_s3_upload_response
from dbmisvc_test.responses import mock_fileservice_archivefile_download_response
from dbmisvc_test.responses import mock_reg_get_names_response
from dbmisvc_test.responses import mock_authz_get_permission_response
from dbmisvc_test.responses import mock_authz_remove_permission_response
from dbmisvc_test.responses import mock_authz_grant_permission_response
from django_q.models import Task

from test.test_case import HypatioTestCase
from projects.models import DataProject
from projects.models import Participant
from projects.models import AgreementForm
from projects.models import HostedFile
from projects.models import SignedAgreementForm
from projects.models import Team
from projects.models import TeamComment
from projects.models import ChallengeTask
from projects.models import ChallengeTaskSubmission
from manage.models import ChallengeTaskSubmissionExport


class DataProjectSetRegistrationStatusTestCase(HypatioTestCase):

    # Set the URL pattern for this view.
    url_pattern = "manage:set-dataproject-registration-status"

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
                    mock_authz_get_permission_response(self.admin.jwt, f"Hypatio.{self.project.project_key}", "MANAGE"),
                ],
                self.admin_client,
                Method.POST,
                self.url,
                {
                    "project_key": self.project.project_key,
                    "registration_status": "open",
                },
                200,
                "text/html; charset=utf-8",
                True,
                True,
            ),
            RequestResponse(
                "User request",
                [
                    mock_authz_get_permission_response(self.user.jwt, f"Hypatio.{self.project.project_key}"),
                ],
                self.client,
                Method.POST,
                self.url,
                {
                    "project_key": self.project.project_key,
                    "registration_status": "open",
                },
                403,
                "text/html; charset=utf-8",
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
                self.admin_client,
                Method.POST,
                self.url,
                {
                    "project-key": self.project.project_key,
                    "registration_status": "open",
                },
                400,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid project parameter value request",
                [
                    mock_authz_get_permission_response(self.admin.jwt, f"Hypatio.{self.project.project_key}", "MANAGE"),
                ],
                self.admin_client,
                Method.POST,
                self.url,
                {
                    "project_key": "not-a-project-key",
                    "registration_status": "open",
                },
                404,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Missing registration property parameter request",
                [
                ],
                self.admin_client,
                Method.POST,
                self.url,
                {
                    "project_key": self.project.project_key,
                },
                400,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid registration parameter key request",
                [
                ],
                self.admin_client,
                Method.POST,
                self.url,
                {
                    "project_key": self.project.project_key,
                    "registration": "open",
                },
                400,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid registration parameter value request",
                [
                    mock_authz_get_permission_response(self.admin.jwt, f"Hypatio.{self.project.project_key}", "MANAGE"),
                ],
                self.admin_client,
                Method.POST,
                self.url,
                {
                    "project_key": self.project.project_key,
                    "registration_status": "open-ish",
                },
                400,
                "text/html; charset=utf-8",
            ),
        ]

    def test_set_dataproject_open(self):

        # Get the successful request response
        request_response = next(iter(r for r in self.request_responses if r.successful))

        # Set the visibility
        request_response.data["registration_status"] = "open"

        # Make the request
        request_response.call()

        # Fetch the data project
        data_project = DataProject.objects.get(id=self.project.id)

        # Make assertions
        self.assertEqual(data_project.registration_open, True)

    def test_set_dataproject_closed(self):

        # Get the successful request response
        request_response = next(iter(r for r in self.request_responses if r.successful))

        # Set the visibility
        request_response.data["registration_status"] = "closed"

        # Make the request
        request_response.call()

        # Fetch the data project
        data_project = DataProject.objects.get(id=self.project.id)

        # Make assertions
        self.assertEqual(data_project.registration_open, False)


class DataProjectSetVisibleStatusTestCase(HypatioTestCase):

    # Set the URL pattern for this view.
    url_pattern = "manage:set-dataproject-visible-status"

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
                    mock_authz_get_permission_response(self.admin.jwt, f"Hypatio.{self.project.project_key}", "MANAGE"),
                ],
                self.admin_client,
                Method.POST,
                self.url,
                {
                    "project_key": self.project.project_key,
                    "visible_status": "invisible",
                },
                200,
                "text/html; charset=utf-8",
                True,
                True,
            ),
            RequestResponse(
                "User request",
                [
                    mock_authz_get_permission_response(self.user.jwt, f"Hypatio.{self.project.project_key}"),
                ],
                self.client,
                Method.POST,
                self.url,
                {
                    "project_key": self.project.project_key,
                    "visible_status": "visible",
                },
                403,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Anonymous request",
                [],
                self.anonymous_client,
                Method.POST,
                self.url,
                {
                    "project_key": self.project.project_key,
                    "visible_status": "visible",
                },
                302,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid project parameter key request",
                [
                ],
                self.admin_client,
                Method.POST,
                self.url,
                {
                    "project-key": self.project.project_key,
                    "visible_status": "visible",
                },
                400,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid project parameter value request",
                [
                    mock_authz_get_permission_response(self.admin.jwt, f"Hypatio.{self.project.project_key}", "MANAGE"),
                ],
                self.admin_client,
                Method.POST,
                self.url,
                {
                    "project_key": "not-a-project-key",
                    "visible_status": "visible",
                },
                404,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Missing visibility property parameter request",
                [
                ],
                self.admin_client,
                Method.POST,
                self.url,
                {
                    "project_key": self.project.project_key,
                },
                400,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid visibilility parameter key request",
                [
                ],
                self.admin_client,
                Method.POST,
                self.url,
                {
                    "project_key": self.project.project_key,
                    "visible": "visible",
                },
                400,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid visibilility parameter value request",
                [
                    mock_authz_get_permission_response(self.admin.jwt, f"Hypatio.{self.project.project_key}", "MANAGE"),
                ],
                self.admin_client,
                Method.POST,
                self.url,
                {
                    "project_key": self.project.project_key,
                    "visible_status": "somewhat-visible",
                },
                400,
                "text/html; charset=utf-8",
            ),
        ]

    def test_set_dataproject_visible(self):

        # Get the successful request response
        request_response = next(iter(r for r in self.request_responses if r.successful))

        # Set the visibility
        request_response.data["visible_status"] = "visible"

        # Make the request
        request_response.call()

        # Fetch the data project
        data_project = DataProject.objects.get(id=self.project.id)

        # Make assertions
        self.assertEqual(data_project.visible, True)

    def test_set_dataproject_invisible(self):

        # Get the successful request response
        request_response = next(iter(r for r in self.request_responses if r.successful))

        # Set the visibility
        request_response.data["visible_status"] = "invisible"

        # Make the request
        request_response.call()

        # Fetch the data project
        data_project = DataProject.objects.get(id=self.project.id)

        # Make assertions
        self.assertEqual(data_project.visible, False)


class DataProjectSetDetailsTestCase(HypatioTestCase):

    # Set the URL pattern for this view.
    url_pattern = "manage:set-dataproject-details"

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

        # Set project details to set
        self.project_name = "New Test Project"
        self.project_short_description = "This is a short description for the new test project"
        self.project_description = "This is a long description for the new test project"

        # Set the request response objects
        self.request_responses = [
            RequestResponse(
                "Successful request",
                [
                    mock_authz_get_permission_response(self.admin.jwt, f"Hypatio.{self.project.project_key}", "MANAGE"),
                ],
                self.admin_client,
                Method.POST,
                self.url,
                {
                    "project_key": self.project.project_key,
                    "name": self.project_name,
                    "description": self.project_description,
                    "short-description": self.project_short_description,
                },
                200,
                "text/html; charset=utf-8",
                True,
                True,
            ),
            RequestResponse(
                "User request",
                [
                    mock_authz_get_permission_response(self.user.jwt, f"Hypatio.{self.project.project_key}"),
                ],
                self.client,
                Method.POST,
                self.url,
                {
                    "project_key": self.project.project_key,
                    "name": self.project_name,
                    "description": self.project_description,
                    "short-description": self.project_short_description,
                },
                403,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Anonymous request",
                [],
                self.anonymous_client,
                Method.POST,
                self.url,
                {
                    "project_key": self.project.project_key,
                    "name": self.project_name,
                    "description": self.project_description,
                    "short-description": self.project_short_description,
                },
                302,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid project parameter key request",
                [
                ],
                self.admin_client,
                Method.POST,
                self.url,
                {
                    "project-key": self.project.project_key,
                    "name": self.project_name,
                    "description": self.project_description,
                    "short-description": self.project_short_description,
                },
                400,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid project parameter value request",
                [
                    mock_authz_get_permission_response(self.admin.jwt, f"Hypatio.{self.project.project_key}", "MANAGE"),
                ],
                self.admin_client,
                Method.POST,
                self.url,
                {
                    "project_key": "not-a-project-key",
                    "name": self.project_name,
                    "description": self.project_description,
                    "short-description": self.project_short_description,
                },
                404,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Missing project property parameter request",
                [
                ],
                self.admin_client,
                Method.POST,
                self.url,
                {
                    "project_key": self.project.project_key,
                    "name": self.project_name,
                    "description": self.project_description,
                },
                400,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid project property parameter key request",
                [
                ],
                self.admin_client,
                Method.POST,
                self.url,
                {
                    "project_key": self.project.project_key,
                    "name": self.project_name,
                    "description": self.project_description,
                    "short_description": self.project_short_description,
                },
                400,
                "text/html; charset=utf-8",
            ),
        ]

    def test_set_dataproject_details(self):

        # Get the successful request response
        request_response = next(iter(r for r in self.request_responses if r.successful))

        # Make the request
        request_response.call()

        # Fetch the data project
        data_project = DataProject.objects.get(id=self.project.id)

        # Make assertions
        self.assertEqual(data_project.name, self.project_name)
        self.assertEqual(data_project.description, self.project_description)
        self.assertEqual(data_project.short_description, self.project_short_description)

class DataProjectGetStaticAgreementFormHtmlTestCase(HypatioTestCase):

    # Set the URL pattern for this view.
    url_pattern = "manage:get-static-agreement-form-html"

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
                    mock_authz_get_permission_response(self.admin.jwt, f"Hypatio.{self.project.project_key}", "MANAGE"),
                ],
                self.admin_client,
                Method.GET,
                self.url,
                {
                    "project-key": self.project.project_key,
                    "form-id": self.agreement_form.id,
                },
                200,
                "text/html; charset=utf-8",
                True,
                True,
            ),
            RequestResponse(
                "User request",
                [
                    mock_authz_get_permission_response(self.user.jwt, f"Hypatio.{self.project.project_key}"),
                ],
                self.client,
                Method.GET,
                self.url,
                {
                    "project-key": self.project.project_key,
                    "form-id": self.agreement_form.id,
                },
                403,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Anonymous request",
                [],
                self.anonymous_client,
                Method.GET,
                self.url,
                {
                    "project-key": self.project.project_key,
                    "form-id": self.agreement_form.id,
                },
                302,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid project parameter key request",
                [
                ],
                self.admin_client,
                Method.GET,
                self.url,
                {
                    "project": self.project.project_key,
                    "form-id": self.agreement_form.id,
                },
                400,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid project parameter value request",
                [
                    mock_authz_get_permission_response(self.admin.jwt, f"Hypatio.{self.project.project_key}", "MANAGE"),
                ],
                self.admin_client,
                Method.GET,
                self.url,
                {
                    "project-key": "not-a-project-key",
                    "form-id": self.agreement_form.id,
                },
                404,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid form parameter key request",
                [
                ],
                self.admin_client,
                Method.GET,
                self.url,
                {
                    "project-key": self.project.project_key,
                    "form": self.agreement_form.id,
                },
                400,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid form parameter value request",
                [
                    mock_authz_get_permission_response(self.admin.jwt, f"Hypatio.{self.project.project_key}", "MANAGE"),
                ],
                self.admin_client,
                Method.GET,
                self.url,
                {
                    "project-key": self.project.project_key,
                    "form-id": 9999,
                },
                404,
                "text/html; charset=utf-8",
            ),
        ]


class ManageGetHostedFileEditFormTestCase(HypatioTestCase):

    # Set the URL pattern for this view.
    url_pattern = "manage:get-hosted-file-edit-form"

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        # Create a project
        cls.project = DataProject.objects.create(
            name='Test Project',
            description='This is a test project',
            project_key='test_project',
        )

        # Create a hosted file
        cls.hosted_file = HostedFile.objects.create(
            project=cls.project,
            long_name='test_hosted_file',
            file_name='test_hosted_file.html',
            file_location='s3://some-random-bucket/location',
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
                    mock_authz_get_permission_response(self.admin.jwt, f"Hypatio.{self.project.project_key}", "MANAGE"),
                ],
                self.admin_client,
                Method.GET,
                self.url,
                {
                    "project-key": self.project.project_key,
                    "hosted-file-uuid": self.hosted_file.uuid
                },
                200,
                "text/html; charset=utf-8",
                True,
                True,
            ),
            RequestResponse(
                "User request",
                [
                    mock_authz_get_permission_response(self.user.jwt, f"Hypatio.{self.project.project_key}"),
                ],
                self.client,
                Method.GET,
                self.url,
                {
                    "project-key": self.project.project_key,
                    "hosted-file-uuid": self.hosted_file.uuid
                },
                403,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Anonymous request",
                [],
                self.anonymous_client,
                Method.GET,
                self.url,
                {
                    "project-key": self.project.project_key,
                    "hosted-file-uuid": self.hosted_file.uuid
                },
                302,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid project parameter key request",
                [
                ],
                self.admin_client,
                Method.GET,
                self.url,
                {
                    "project": self.project.project_key,
                    "hosted-file-uuid": self.hosted_file.uuid
                },
                400,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid project parameter value request",
                [
                    mock_authz_get_permission_response(self.admin.jwt, f"Hypatio.{self.project.project_key}", "MANAGE"),
                ],
                self.admin_client,
                Method.GET,
                self.url,
                {
                    "project-key": "not-a-project-key",
                    "hosted-file-uuid": self.hosted_file.uuid
                },
                404,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid file parameter key request",
                [
                ],
                self.admin_client,
                Method.GET,
                self.url,
                {
                    "project-key": self.project.project_key,
                    "file-uuid": self.hosted_file.uuid
                },
                400,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid file parameter value request",
                [
                    mock_authz_get_permission_response(self.admin.jwt, f"Hypatio.{self.project.project_key}", "MANAGE"),
                ],
                self.admin_client,
                Method.GET,
                self.url,
                {
                    "project-key": self.project.project_key,
                    "hosted-file-uuid": str(uuid.uuid4()),
                },
                404,
                "text/html; charset=utf-8",
            ),
        ]


class ManageGetHostedFileLogsTestCase(HypatioTestCase):

    # Set the URL pattern for this view.
    url_pattern = "manage:get-hosted-file-logs"

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        # Create a project
        cls.project = DataProject.objects.create(
            name='Test Project',
            description='This is a test project',
            project_key='test_project',
        )

        # Create a hosted file
        cls.hosted_file = HostedFile.objects.create(
            project=cls.project,
            long_name='test_hosted_file',
            file_name='test_hosted_file.html',
            file_location='s3://some-random-bucket/location',
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
                    mock_authz_get_permission_response(self.admin.jwt, f"Hypatio.{self.project.project_key}", "MANAGE"),
                ],
                self.admin_client,
                Method.GET,
                self.url,
                {
                    "project-key": self.project.project_key,
                    "hosted-file-uuid": self.hosted_file.uuid
                },
                200,
                "text/html; charset=utf-8",
                True,
                True,
            ),
            RequestResponse(
                "User request",
                [
                    mock_authz_get_permission_response(self.user.jwt, f"Hypatio.{self.project.project_key}"),
                ],
                self.client,
                Method.GET,
                self.url,
                {
                    "project-key": self.project.project_key,
                    "hosted-file-uuid": self.hosted_file.uuid
                },
                403,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Anonymous request",
                [],
                self.anonymous_client,
                Method.GET,
                self.url,
                {
                    "project-key": self.project.project_key,
                    "hosted-file-uuid": self.hosted_file.uuid
                },
                302,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid project parameter key request",
                [
                ],
                self.admin_client,
                Method.GET,
                self.url,
                {
                    "project": self.project.project_key,
                    "hosted-file-uuid": self.hosted_file.uuid
                },
                400,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid project parameter value request",
                [
                    mock_authz_get_permission_response(self.admin.jwt, f"Hypatio.{self.project.project_key}", "MANAGE"),
                ],
                self.admin_client,
                Method.GET,
                self.url,
                {
                    "project-key": "not-a-project-key",
                    "hosted-file-uuid": self.hosted_file.uuid
                },
                404,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid file parameter key request",
                [
                ],
                self.admin_client,
                Method.GET,
                self.url,
                {
                    "project-key": self.project.project_key,
                    "file-uuid": self.hosted_file.uuid
                },
                400,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid file parameter value request",
                [
                    mock_authz_get_permission_response(self.admin.jwt, f"Hypatio.{self.project.project_key}", "MANAGE"),
                ],
                self.admin_client,
                Method.GET,
                self.url,
                {
                    "project-key": self.project.project_key,
                    "hosted-file-uuid": str(uuid.uuid4()),
                },
                404,
                "text/html; charset=utf-8",
            ),
        ]


class ManageProcessHostedFileEditFormSubmissionTestCase(HypatioTestCase):

    # Set the URL pattern for this view.
    url_pattern = "manage:process-hosted-file-edit-form-submission"

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        # Create a project
        cls.project = DataProject.objects.create(
            name='Test Project',
            description='This is a test project',
            project_key='test_project',
        )

        # Create a hosted file
        cls.hosted_file = HostedFile.objects.create(
            project=cls.project,
            long_name='test_hosted_file',
            file_name='test_hosted_file.html',
            file_location='s3://some-random-bucket/location',
            description="Some description of this test file",
            opened_time=datetime.now(timezone.utc),
            closed_time=datetime.now(timezone.utc),
        )

    def setUp(self):
        super().setUp()

        # Set the URL for the tests
        self.url = reverse(self.url_pattern)

        self.request_responses = [
            RequestResponse(
                "Successful request",
                [
                    mock_authz_get_permission_response(self.admin.jwt, f"Hypatio.{self.project.project_key}", "MANAGE"),
                ],
                self.admin_client,
                Method.POST,
                self.url,
                {
                    "file-uuid": self.hosted_file.uuid,
                    "project": self.hosted_file.project.id,
                    "long_name": self.hosted_file.long_name,
                    "file_name": self.hosted_file.file_name,
                    "file_location": self.hosted_file.file_location,
                    "description": self.hosted_file.description,
                    "opened_time": self.hosted_file.opened_time,
                    "closed_time": self.hosted_file.closed_time,
                },
                200,
                "text/html; charset=utf-8",
                True,
                True,
            ),
            RequestResponse(
                "User request",
                [
                    mock_authz_get_permission_response(self.user.jwt, f"Hypatio.{self.project.project_key}"),
                ],
                self.client,
                Method.POST,
                self.url,
                {
                    "file-uuid": self.hosted_file.uuid,
                    "project": self.hosted_file.project.id,
                    "long_name": self.hosted_file.long_name,
                    "file_name": self.hosted_file.file_name,
                    "file_location": self.hosted_file.file_location,
                    "description": self.hosted_file.description,
                    "opened_time": self.hosted_file.opened_time,
                    "closed_time": self.hosted_file.closed_time,
                },
                403,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Anonymous request",
                [],
                self.anonymous_client,
                Method.POST,
                self.url,
                {
                    "file-uuid": self.hosted_file.uuid,
                    "project": self.hosted_file.project.id,
                    "long_name": self.hosted_file.long_name,
                    "file_name": self.hosted_file.file_name,
                    "file_location": self.hosted_file.file_location,
                    "description": self.hosted_file.description,
                    "opened_time": self.hosted_file.opened_time,
                    "closed_time": self.hosted_file.closed_time,
                },
                302,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid project parameter key request",
                [
                ],
                self.admin_client,
                Method.POST,
                self.url,
                {
                    "file-uuid": self.hosted_file.uuid,
                    "project-id": self.hosted_file.project.id,
                    "long_name": self.hosted_file.long_name,
                    "file_name": self.hosted_file.file_name,
                    "file_location": self.hosted_file.file_location,
                    "description": self.hosted_file.description,
                    "opened_time": self.hosted_file.opened_time,
                    "closed_time": self.hosted_file.closed_time,
                },
                400,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid project parameter value request",
                [
                    mock_authz_get_permission_response(self.admin.jwt, f"Hypatio.{self.project.project_key}", "MANAGE"),
                ],
                self.admin_client,
                Method.POST,
                self.url,
                {
                    "file-uuid": self.hosted_file.uuid,
                    "project": 9999,
                    "long_name": self.hosted_file.long_name,
                    "file_name": self.hosted_file.file_name,
                    "file_location": self.hosted_file.file_location,
                    "description": self.hosted_file.description,
                    "opened_time": self.hosted_file.opened_time,
                    "closed_time": self.hosted_file.closed_time,
                },
                404,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid file parameter key request",
                [
                ],
                self.admin_client,
                Method.POST,
                self.url,
                {
                    "file": self.hosted_file.uuid,
                    "project": self.hosted_file.project.id,
                    "long_name": self.hosted_file.long_name,
                    "file_name": self.hosted_file.file_name,
                    "file_location": self.hosted_file.file_location,
                    "description": self.hosted_file.description,
                    "opened_time": self.hosted_file.opened_time,
                    "closed_time": self.hosted_file.closed_time,
                },
                400,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid file parameter value request",
                [
                    mock_authz_get_permission_response(self.admin.jwt, f"Hypatio.{self.project.project_key}", "MANAGE"),
                ],
                self.admin_client,
                Method.POST,
                self.url,
                {
                    "file-uuid": str(uuid.uuid4()),
                    "project": self.hosted_file.project.id,
                    "long_name": self.hosted_file.long_name,
                    "file_name": self.hosted_file.file_name,
                    "file_location": self.hosted_file.file_location,
                    "description": self.hosted_file.description,
                    "opened_time": self.hosted_file.opened_time,
                    "closed_time": self.hosted_file.closed_time,
                },
                404,
                "text/html; charset=utf-8",
            ),
        ]

    def test_process_hosted_file_edit_form_submission(self):

        # Get the successful request
        request_response = next(iter(r for r in self.request_responses if r.successful))

        # Modify a field
        request_response.data["description"] = f"This is a random new description: {''.join(random.choices(string.ascii_uppercase + string.digits, k=10))}"

        # Make the request
        request_response.call()

        # Fetch the object
        hosted_file = HostedFile.objects.get(uuid=self.hosted_file.uuid)

        # Compare data
        self.assertEqual(hosted_file.description, request_response.data["description"])


class ManageDownloadSignedFormTestCase(HypatioTestCase):

    # Set the URL pattern for this view.
    url_pattern = "manage:download-signed-form"

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

        # Create an signed agreement form
        cls.signed_agreement_form = SignedAgreementForm.objects.create(
            user=cls.user,
            project=cls.project,
            agreement_form=cls.agreement_form,
        )

    def setUp(self):
        super().setUp()

        # Set the URL for the tests.
        self.url = reverse(self.url_pattern)

        self.request_responses = [
            RequestResponse(
                "Successful request",
                [
                    mock_authz_get_permission_response(self.admin.jwt, f"Hypatio.{self.project.project_key}", "MANAGE"),
                ],
                self.admin_client,
                Method.GET,
                self.url,
                {
                    "form_id": self.signed_agreement_form.id,
                },
                200,
                "text/plain",
                True,
                True,
            ),
            RequestResponse(
                "User request",
                [
                    mock_authz_get_permission_response(self.user.jwt, f"Hypatio.{self.project.project_key}"),
                ],
                self.client,
                Method.GET,
                self.url,
                {
                    "form_id": self.signed_agreement_form.id,
                },
                403,
                "text/html; charset=utf-8"
            ),
            RequestResponse(
                "Anonymous request",
                [],
                self.anonymous_client,
                Method.GET,
                self.url,
                {
                    "form_id": self.signed_agreement_form.id,
                },
                302,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid form parameter key request",
                [
                ],
                self.admin_client,
                Method.GET,
                self.url,
                {
                    "form-id": self.signed_agreement_form.id,
                },
                400,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid form parameter value request",
                [
                    mock_authz_get_permission_response(self.admin.jwt, f"Hypatio.{self.project.project_key}", "MANAGE"),
                ],
                self.admin_client,
                Method.GET,
                self.url,
                {
                    "form_id": 9999,
                },
                404,
                "text/html; charset=utf-8",
            ),
        ]


class ManageGetSignedFormStatusTestCase(HypatioTestCase):

    # Set the URL pattern for this view.
    url_pattern = "manage:get-signed-form-status"

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

        # Create an signed agreement form
        cls.signed_agreement_form = SignedAgreementForm.objects.create(
            user=cls.user,
            project=cls.project,
            agreement_form=cls.agreement_form,
        )

    def setUp(self):
        super().setUp()

        # Set the URL for the tests.
        self.url = reverse(self.url_pattern)

        self.request_responses = [
            RequestResponse(
                "Successful request",
                [
                    mock_authz_get_permission_response(self.admin.jwt, f"Hypatio.{self.project.project_key}", "MANAGE"),
                ],
                self.admin_client,
                Method.POST,
                self.url,
                {
                    "form_id": self.signed_agreement_form.id,
                },
                200,
                "text/html; charset=utf-8",
                True,
                True,
            ),
            RequestResponse(
                "User authorization check",
                [
                    mock_authz_get_permission_response(self.user.jwt, f"Hypatio.{self.project.project_key}"),
                ],
                self.client,
                Method.POST,
                self.url,
                {
                    "form_id": self.signed_agreement_form.id,
                },
                403,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Anonymous authorization check",
                [],
                self.anonymous_client,
                Method.POST,
                self.url,
                {
                    "form_id": self.signed_agreement_form.id,
                    },
                302,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid signed agreement form parameter value request",
                [
                    mock_authz_get_permission_response(self.admin.jwt, f"Hypatio.{self.project.project_key}", "MANAGE"),
                ],
                self.admin_client,
                Method.POST,
                self.url,
                {
                    "form_id": "999999",
                },
                404,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid signed agreement form parameter key request",
                [
                ],
                self.admin_client,
                Method.POST,
                self.url,
                {
                    "form-id": self.signed_agreement_form.id,
                },
                400,
                "text/html; charset=utf-8",
            ),
        ]


class ManageChangeSignedFormStatusTestCase(HypatioTestCase):

    # Set the URL pattern for this view.
    url_pattern = "manage:change-signed-form-status"

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

        # Create an signed agreement form
        cls.signed_agreement_form = SignedAgreementForm.objects.create(
            user=cls.user,
            project=cls.project,
            agreement_form=cls.agreement_form,
        )

    def setUp(self):
        super().setUp()

        # Set the URL to change project details.
        self.url = reverse(self.url_pattern)

        self.request_responses = [
            RequestResponse(
                "Successful rejected form request",
                [
                    mock_authz_get_permission_response(self.admin.jwt, f"Hypatio.{self.project.project_key}", "MANAGE"),
                ],
                self.admin_client,
                Method.POST,
                self.url,
                {
                    "form_id": self.signed_agreement_form.id,
                    "status": "rejected",
                    "administrator_message": "This is a test message",
                },
                200,
                "text/html; charset=utf-8",
                True,
                True,
            ),
            RequestResponse(
                "Successful approved form request",
                [
                    mock_authz_get_permission_response(self.admin.jwt, f"Hypatio.{self.project.project_key}", "MANAGE"),
                ],
                self.admin_client,
                Method.POST,
                self.url,
                {
                    "form_id": self.signed_agreement_form.id,
                    "status": "approved",
                },
                200,
                "text/html; charset=utf-8",
                True,
                True,
            ),
            RequestResponse(
                "User request",
                [
                    mock_authz_get_permission_response(self.user.jwt, f"Hypatio.{self.project.project_key}"),
                ],
                self.client,
                Method.POST,
                self.url,
                {
                    "form_id": self.signed_agreement_form.id,
                    "status": "A",
                    "administrator_message": "This is a test message",
                },
                403,
                "text/html; charset=utf-8"
            ),
            RequestResponse(
                "Anonymous request",
                [],
                self.anonymous_client,
                Method.POST,
                self.url,
                {
                    "form_id": self.signed_agreement_form.id,
                    "status": "A",
                    "administrator_message": "This is a test message",
                },
                302,
                "text/html; charset=utf-8"
            ),
            RequestResponse(
                "Missing administrator message parameter request",
                [
                    #mock_authz_get_permission_response(self.admin.jwt, f"Hypatio.{self.project.project_key}", "MANAGE"),
                ],
                self.admin_client,
                Method.POST,
                self.url,
                {
                    "form_id": self.signed_agreement_form.id,
                    "status": "rejected",
                },
                400,
                "text/html; charset=utf-8"
            ),
            RequestResponse(
                "Invalid signed agreement form parameter value request",
                [
                    mock_authz_get_permission_response(self.admin.jwt, f"Hypatio.{self.project.project_key}", "MANAGE"),
                ],
                self.admin_client,
                Method.POST,
                self.url,
                {
                    "form_id": "999999",
                    "status": "rejected",
                    "administrator_message": "This is a test message",
                },
                404,
                "text/html; charset=utf-8"
            ),
            RequestResponse(
                "Invalid parameter key request",
                [
                    #mock_authz_get_permission_response(self.admin.jwt, f"Hypatio.{self.project.project_key}", "MANAGE"),
                ],
                self.admin_client,
                Method.POST,
                self.url,
                {
                    "form-id": self.signed_agreement_form.id,
                    "status": "approved",
                    "administrator_message": "This is a test message",
                },
                400,
                "text/html; charset=utf-8"
            ),
            RequestResponse(
                "Invalid status parameter value request",
                [
                    mock_authz_get_permission_response(self.admin.jwt, f"Hypatio.{self.project.project_key}", "MANAGE"),
                ],
                self.admin_client,
                Method.POST,
                self.url,
                {
                    "form_id": self.signed_agreement_form.id,
                    "status": "R",
                    "administrator_message": "This is a test message",
                },
                400,
                "text/html; charset=utf-8"
            ),
        ]

    def test_change_signed_form_status_approved(self):

        # Get the request response
        request_response = next(iter(r for r in self.request_responses if r.successful and r.data.get("status") == "approved"))

        # Make the request
        request_response.call()

        # Make assertions
        self.assertEqual(SignedAgreementForm.objects.get(id=self.signed_agreement_form.id).status, "A")

    def test_change_signed_form_status_rejected(self):

        # Get the request response
        request_response = next(iter(r for r in self.request_responses if r.successful and r.data.get("status") == "rejected"))

        # Make the request
        request_response.call()

        # Make assertions
        self.assertEqual(SignedAgreementForm.objects.get(id=self.signed_agreement_form.id).status, "R")
        self.assertEqual(mail.outbox[0].subject, "DBMI Portal - Signed Form Rejected")

class ManageSaveTeamCommentTestCase(HypatioTestCase):

    # Set the URL pattern for this view.
    url_pattern = "manage:save-team-comment"

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

    def setUp(self):
        super().setUp()

        # Set the URL to change project details.
        self.url = reverse(self.url_pattern)

        # Set the comment to use
        self.team_comment = "This is a test message"

        self.request_responses = [
            RequestResponse(
                "Admin authorization check",
                [
                    mock_authz_get_permission_response(self.admin.jwt, f"Hypatio.{self.project.project_key}", "MANAGE"),
                ],
                self.admin_client,
                Method.POST,
                self.url,
                {
                    "project": self.project.project_key,
                    "team": self.user.email,
                    "comment": self.team_comment,
                },
                200,
                "text/html; charset=utf-8",
                True,
                True,
            ),
            RequestResponse(
                "User authorization check",
                [
                    mock_authz_get_permission_response(self.user.jwt, f"Hypatio.{self.project.project_key}"),
                ],
                self.client,
                Method.POST,
                self.url,
                {
                    "project": self.project.project_key,
                    "team": self.user.email,
                    "comment": self.team_comment,
                },
                403,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Anonymous authorization check",
                [],
                self.anonymous_client,
                Method.POST,
                self.url,
                {
                    "project": self.project.project_key,
                    "team": self.user.email,
                    "comment": self.team_comment,
                },
                302,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Missing team leader parameter check",
                [
                ],
                self.admin_client,
                Method.POST,
                self.url,
                {
                    "project": self.project.project_key,
                    "comment": self.team_comment,
                },
                400,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid team leader parameter check",
                [
                    mock_authz_get_permission_response(self.admin.jwt, f"Hypatio.{self.project.project_key}", "MANAGE"),
                ],
                self.admin_client,
                Method.POST,
                self.url,
                {
                    "project": self.project.project_key,
                    "team": "another@email.com",
                    "comment": self.team_comment,
                },
                404,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Incorrect parameter name check",
                [
                ],
                self.admin_client,
                Method.POST,
                self.url,
                {
                    "project-key": self.project.project_key,
                    "team": self.user.email,
                    "comment": self.team_comment,
                },
                400,
                "text/html; charset=utf-8",
            ),
        ]

    def test_save_team_comment(self):

        # Get successful request response
        request_response = next(iter([r for r in self.request_responses if r.successful]))

        # Call it
        request_response.call()

        # Make assertions
        self.assertEqual(TeamComment.objects.filter(team__team_leader__email=self.user.email).all().count(), 1)
        self.assertEqual(TeamComment.objects.filter(team__team_leader__email=self.user.email).first().text, self.team_comment)


class ManageSetTeamStatusTestCase(HypatioTestCase):

    # Set the URL pattern for this view.
    url_pattern = "manage:set-team-status"

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

        # Set the URL to change project details.
        self.url = reverse(self.url_pattern)

        self.request_responses = [
            RequestResponse(
                "Successful team ready request",
                [
                    mock_authz_get_permission_response(self.admin.jwt, f"Hypatio.{self.project.project_key}", "MANAGE"),
                ],
                self.admin_client,
                Method.POST,
                self.url,
                {
                    "project": self.project.project_key,
                    "team": self.user.email,
                    "status": "ready",
                },
                200,
                "text/html; charset=utf-8",
                True,
                True,
            ),
            RequestResponse(
                "Successful team active request",
                [
                    mock_authz_get_permission_response(self.admin.jwt, f"Hypatio.{self.project.project_key}", "MANAGE"),
                    mock_authz_grant_permission_response(self.admin.jwt),

                ],
                self.admin_client,
                Method.POST,
                self.url,
                {
                    "project": self.project.project_key,
                    "team": self.user.email,
                    "status": "active",
                },
                200,
                "text/html; charset=utf-8",
                True,
                True,
            ),
            RequestResponse(
                "Successful team deactivated request",
                [
                    mock_authz_get_permission_response(self.admin.jwt, f"Hypatio.{self.project.project_key}", "MANAGE"),
                    mock_authz_remove_permission_response(self.admin.jwt),

                ],
                self.admin_client,
                Method.POST,
                self.url,
                {
                    "project": self.project.project_key,
                    "team": self.user.email,
                    "status": "deactivated",
                },
                200,
                "text/html; charset=utf-8",
                True,
                True,
            ),
            RequestResponse(
                "User request",
                [
                    mock_authz_get_permission_response(self.user.jwt, f"Hypatio.{self.project.project_key}"),
                ],
                self.client,
                Method.POST,
                self.url,
                {
                    "project": self.project.project_key,
                    "team": self.user.email,
                    "status": "ready",
                },
                403,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Anonymous request",
                [],
                self.anonymous_client,
                Method.POST,
                self.url,
                {
                    "project": self.project.project_key,
                    "team": self.user.email,
                    "status": "ready",
                },
                302,
                "text/html; charset=utf-8"
            ),
            RequestResponse(
                "Missing parameter request",
                [],
                self.admin_client,
                Method.POST,
                self.url,
                {
                    "team": self.user.email,
                    "status": "ready",
                },
                400,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid team leader parameter value request",
                [
                    mock_authz_get_permission_response(self.admin.jwt, f"Hypatio.{self.project.project_key}", "MANAGE"),
                ],
                self.admin_client,
                Method.POST,
                self.url,
                {
                    "project": self.project.project_key,
                    "team": "some-other@email.com",
                    "status": "ready",
                },
                404,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid parameter key request",
                [],
                self.admin_client,
                Method.POST,
                self.url,
                {
                    "project-key": self.project.project_key,
                    "team": self.user.email,
                    "status": "ready",
                },
                400,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid project parameter value request",
                [
                    mock_authz_get_permission_response(self.admin.jwt, f"Hypatio.{self.project.project_key}", "MANAGE"),
                ],
                self.admin_client,
                Method.POST,
                self.url,
                {
                    "project": self.project.id,
                    "team": self.user.email,
                    "status": "ready",
                },
                404,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid status parameter value request",
                [
                    mock_authz_get_permission_response(self.admin.jwt, f"Hypatio.{self.project.project_key}", "MANAGE"),
                ],
                self.admin_client,
                Method.POST,
                self.url,
                {
                    "project": self.project.project_key,
                    "team": self.user.email,
                    "status": "activated",
                },
                400,
                "text/html; charset=utf-8",
            ),
        ]

    def test_set_team_ready(self):

        # Get successful request
        request_response = next(iter([r for r in self.request_responses if r.successful and r.data.get("status") == "ready"]))

        # Call it
        request_response.call()

        # Check the data
        self.assertEqual(Team.objects.get(id=self.team.id).status, "Ready")
        for participant in Participant.objects.filter(team=self.team):
            self.assertIsNone(participant.permission)

        # Check emails sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "DBMI Portal - Team Status Changed")
        self.assertCountEqual(mail.outbox[0].recipients(), [self.user.email, self.team_member_a.email, self.team_member_b.email])

    def test_set_team_active(self):

        # Get successful request
        request_response = next(iter([r for r in self.request_responses if r.successful and r.data.get("status") == "active"]))

        # Fetch the AuthZ response mock
        permission_response = request_response.get_response_mock(Method.POST, "create_item_view_permission_record")

        # Call it
        request_response.call()

        # Check the data
        self.assertEqual(Team.objects.get(id=self.team.id).status, "Active")
        for participant in Participant.objects.filter(team=self.team):
            self.assertEqual(participant.permission, "VIEW")

        # Check emails sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "DBMI Portal - Team Status Changed")
        self.assertCountEqual(mail.outbox[0].recipients(), [self.user.email, self.team_member_a.email, self.team_member_b.email])

        # Check transactions with authorization server
        self.assertEqual(len(permission_response.calls), Participant.objects.filter(team=self.team).count())

    def test_set_team_deactivated(self):

        # Get successful request
        active_request_response = next(iter([r for r in self.request_responses if r.successful and r.data.get("status") == "active"]))

        # Fetch the AuthZ response mock
        permission_response = active_request_response.get_response_mock(Method.POST, "create_item_view_permission_record")

        # Call it
        active_request_response.call()

        self.assertEqual(Team.objects.get(id=self.team.id).status, "Active")
        for participant in Participant.objects.filter(team=self.team):
            self.assertEqual(participant.permission, "VIEW")

        # Check transactions with authorization server
        self.assertEqual(len(permission_response.calls), Participant.objects.filter(team=self.team).count())
        permission_response.calls.reset()

        # Get successful request
        deactivated_request_response = next(iter([r for r in self.request_responses if r.successful and r.data.get("status") == "deactivated"]))

        # Fetch the AuthZ response mock
        permission_response = deactivated_request_response.get_response_mock(Method.POST, "remove_item_view_permission_record")

        # Call it
        deactivated_request_response.call()

        # Check the data
        self.assertEqual(Team.objects.get(id=self.team.id).status, "Deactivated")
        for participant in Participant.objects.filter(team=self.team):
            self.assertIsNone(participant.permission)

        # Check emails sent
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(mail.outbox[0].subject, "DBMI Portal - Team Status Changed")
        self.assertCountEqual(mail.outbox[0].recipients(), [self.user.email, self.team_member_a.email, self.team_member_b.email])

        # Check transactions with authorization server
        self.assertEqual(len(permission_response.calls), Participant.objects.filter(team=self.team).count())


class ManageDeleteTeamTestCase(HypatioTestCase):

    # Set the URL pattern for this view.
    url_pattern = "manage:delete-team"

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
            status="Activated",
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
            permission="VIEW",
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
            permission="VIEW",
        )

    def setUp(self):
        super().setUp()

        # Set the URL to change project details.
        self.url = reverse(self.url_pattern)

        self.request_responses = [
            RequestResponse(
                "Successful request",
                [
                    mock_authz_get_permission_response(self.admin.jwt, f"Hypatio.{self.project.project_key}", "MANAGE"),
                    mock_authz_remove_permission_response(self.admin.jwt),
                ],
                self.admin_client,
                Method.POST,
                self.url,
                {
                    "project": self.project.project_key,
                    "team": self.user.email,
                    "administrator_message": "Your team is deleted",
                },
                200,
                "text/html; charset=utf-8",
                True,
                True,
            ),
            RequestResponse(
                "User request",
                [
                    mock_authz_get_permission_response(self.user.jwt, f"Hypatio.{self.project.project_key}"),
                ],
                self.client,
                Method.POST,
                self.url,
                {
                    "project": self.project.project_key,
                    "team": self.user.email,
                    "administrator_message": "Your team is deleted",
                },
                403,
                "text/html; charset=utf-8"
            ),
            RequestResponse(
                "Anonymous request",
                [],
                self.anonymous_client,
                Method.POST,
                self.url,
                {
                    "project": self.project.project_key,
                    "team": self.user.email,
                    "administrator_message": "Your team is deleted",
                },
                302,
                "text/html; charset=utf-8"
            ),
        ]

    def test_delete_team(self):

        # Get the successful request response
        request_response = next(iter([r for r in self.request_responses if r.successful]))

        # Fetch the AuthZ response mock
        permission_response = request_response.get_response_mock(Method.POST, "remove_item_view_permission_record")

        # Make the request
        request_response.call()

        # Check the data
        self.assertEqual(Team.objects.count(), 0)
        self.assertEqual(Participant.objects.count(), 0)

        # Set participant emails
        participant_emails = [self.user.email, self.team_member_a.email, self.team_member_b.email]

        # Check emails sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "DBMI Portal - Team Deleted")
        self.assertCountEqual(mail.outbox[0].recipients(), participant_emails)

        # Check transactions with authorization server
        self.assertEqual(len(permission_response.calls), len(participant_emails))


class ManageDownloadTeamSubmissionsTestCase(HypatioTestCase):

    # Set the URL pattern for this view.
    url_pattern = "manage:download-team-submissions"

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
        )

        # Setup some submissions
        cls.submission_a = ChallengeTaskSubmission.objects.create(
            uuid=uuid.uuid4(),
            participant=cls.participant,
            challenge_task=cls.challenge_task,
            submission_info='{"test": "submission"}',
        )

    def setUp(self):
        super().setUp()

        # Set the downloaded file content
        self.submission_content = "This is a test submission's file contents in a zip file"
        zip_buffer = io.BytesIO()
        with ZipFile(zip_buffer, "a") as z:
            z.writestr("submission_file.txt", self.submission_content)

        self.request_responses = [
            RequestResponse(
                "Successful request",
                [
                    mock_authz_get_permission_response(self.admin.jwt, f"Hypatio.{self.project.project_key}", "MANAGE"),
                    mock_fileservice_download_archivefile_response(dbmi_settings.FILESERVICE_TOKEN, self.submission_a.uuid, zip_buffer.getvalue()),
                ],
                self.admin_client,
                Method.GET,
                reverse(self.url_pattern, kwargs={
                    "project_key": self.project.project_key,
                    "team_leader_email": self.user.email,
                }),
                {},
                200,
                "application/force-download",
                True,
                True,
            ),
            RequestResponse(
                "User request",
                [
                    mock_authz_get_permission_response(self.user.jwt, f"Hypatio.{self.project.project_key}"),
                ],
                self.client,
                Method.GET,
                reverse(self.url_pattern, kwargs={
                    "project_key": self.project.project_key,
                    "team_leader_email": self.user.email,
                }),
                {},
                403,
                "text/html; charset=utf-8"
            ),
            RequestResponse(
                "Anonymous request",
                [],
                self.anonymous_client,
                Method.GET,
                reverse(self.url_pattern, kwargs={
                    "project_key": self.project.project_key,
                    "team_leader_email": self.user.email,
                }),
                {},
                302,
                "text/html; charset=utf-8"
            ),
            RequestResponse(
                "Invalid project parameter value request",
                [
                    mock_authz_get_permission_response(self.admin.jwt, f"Hypatio.{self.project.project_key}", "MANAGE"),
                ],
                self.admin_client,
                Method.GET,
                reverse(self.url_pattern, kwargs={
                    "project_key": "not-a-project-key",
                    "team_leader_email": self.user.email,
                }),
                {},
                403,
                "text/html; charset=utf-8"
            ),
            RequestResponse(
                "Invalid team leader parameter value request",
                [
                    mock_authz_get_permission_response(self.admin.jwt, f"Hypatio.{self.project.project_key}", "MANAGE"),
                ],
                self.admin_client,
                Method.GET,
                reverse(self.url_pattern, kwargs={
                    "project_key": self.project.project_key,
                    "team_leader_email": "not-a-valid-email@email.com",
                }),
                {},
                404,
                "text/html; charset=utf-8"
            ),
        ]

    def test_team_submissions_download(self):

        # Get the successful request response
        request_response = next(iter([r for r in self.request_responses if r.successful]))

        # Make the request
        response = request_response.call()

        # Check the content type
        self.assertEqual(response["Content-Type"], request_response.content_type)

        # Ensure downloaded file is a zip file
        with ZipFile(io.BytesIO(response.content)) as zf:
            for file in zf.namelist():
                with ZipFile(io.BytesIO(zf.read(file))) as zf_submission:

                    # Check files
                    self.assertIn("submission_info.json", zf_submission.namelist())
                    self.assertIn("submission_file.zip", zf_submission.namelist())

                    # Check submission info
                    self.assertEqual(zf_submission.read("submission_info.json").decode(), self.submission_a.submission_info)

                    # Check submission files
                    with ZipFile(io.BytesIO(zf_submission.read("submission_file.zip"))) as zf_submission_file:
                        for file in zf_submission_file.namelist():
                            self.assertEqual(zf_submission_file.read(file).decode(), self.submission_content)


class ManageDownloadSubmissionTestCase(HypatioTestCase):

    # Set the URL pattern for this view.
    url_pattern = "manage:download-submission"

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
        )

        # Setup some submissions
        cls.submission_a = ChallengeTaskSubmission.objects.create(
            uuid=uuid.uuid4(),
            participant=cls.participant,
            challenge_task=cls.challenge_task,
            submission_info='{"test": "submission"}',
        )

    def setUp(self):
        super().setUp()

        # Set the downloaded file content
        self.submission_content = "This is a test submission's file contents in a zip file"
        zip_buffer = io.BytesIO()
        with ZipFile(zip_buffer, "a") as z:
            z.writestr("submission_file.txt", self.submission_content)

        self.request_responses = [
            RequestResponse(
                "Successful request",
                [
                    mock_authz_get_permission_response(self.admin.jwt, f"Hypatio.{self.project.project_key}", "MANAGE"),
                    mock_fileservice_download_archivefile_response(dbmi_settings.FILESERVICE_TOKEN, self.submission_a.uuid, zip_buffer.getvalue()),
                ],
                self.admin_client,
                Method.GET,
                reverse(self.url_pattern, kwargs={
                    "fileservice_uuid": self.submission_a.uuid,
                }),
                {},
                200,
                "application/force-download",
                True,
                True,
            ),
            RequestResponse(
                "User request",
                [
                    mock_authz_get_permission_response(self.user.jwt, f"Hypatio.{self.project.project_key}"),
                ],
                self.client,
                Method.GET,
                reverse(self.url_pattern, kwargs={
                    "fileservice_uuid": self.submission_a.uuid,
                }),
                {},
                403,
                "text/html; charset=utf-8"
            ),
            RequestResponse(
                "Anonymous request",
                [],
                self.anonymous_client,
                Method.GET,
                reverse(self.url_pattern, kwargs={
                    "fileservice_uuid": self.submission_a.uuid,
                }),
                {},
                302,
                "text/html; charset=utf-8"
            ),
        ]

    def test_submission_download(self):

        # Get the successful request response
        request_response = next(iter([r for r in self.request_responses if r.successful]))

        # Make the request
        response = request_response.call()

        # Check the content type
        self.assertEqual(response["Content-Type"], request_response.content_type)

        # Ensure downloaded file is a zip file
        with ZipFile(io.BytesIO(response.content)) as zf_submission:

            # Check files
            self.assertIn("submission_info.json", zf_submission.namelist())
            self.assertIn("submission_file.zip", zf_submission.namelist())

            # Check submission info
            self.assertEqual(zf_submission.read("submission_info.json").decode(), self.submission_a.submission_info)

            # Check submission files
            with ZipFile(io.BytesIO(zf_submission.read("submission_file.zip"))) as zf_submission_file:
                for file in zf_submission_file.namelist():
                    self.assertEqual(zf_submission_file.read(file).decode(), self.submission_content)


class ManageExportSubmissionsTestCase(HypatioTestCase):

    # Set the URL pattern for this view.
    url_pattern = "manage:export-submissions"

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
        )

        # Setup some submissions
        cls.submission_a = ChallengeTaskSubmission.objects.create(
            uuid=uuid.uuid4(),
            participant=cls.participant,
            challenge_task=cls.challenge_task,
            submission_info='{"test": "Submission A"}',
        )

        cls.submission_a_archivefile = {
            "uuid": str(cls.submission_a),
            "filename": "submission_a.zip",
            "tags": ["test", "submission", "a"],
        }

        # Setup some submissions
        cls.submission_b = ChallengeTaskSubmission.objects.create(
            uuid=uuid.uuid4(),
            participant=cls.participant,
            challenge_task=cls.challenge_task,
            submission_info='{"test": "Submission B"}',
        )

        cls.submission_b_archivefile = {
            "uuid": str(cls.submission_b),
            "filename": "submission_b.zip",
            "tags": ["test", "submission", "b"],
        }

        cls.submissions_export_archivefile = {
            "uuid": str(uuid.uuid4()),
            "filename": "submissions_export.zip",
            "tags": ["test", "submissions", "export"],
        }

    def setUp(self):
        super().setUp()

        # Setup request response objects
        self.request_responses = [
            RequestResponse(
                "Successful request",
                [
                    mock_authz_get_permission_response(self.admin.jwt, f"Hypatio.{self.project.project_key}", "MANAGE"),
                    mock_fileservice_create_archivefile_response(dbmi_settings.FILESERVICE_TOKEN, self.submissions_export_archivefile["uuid"]),
                    mock_fileservice_get_archivefiles_response(dbmi_settings.FILESERVICE_TOKEN, str(self.submission_a.uuid), self.submission_a_archivefile),
                    mock_fileservice_get_archivefiles_response(dbmi_settings.FILESERVICE_TOKEN, str(self.submission_b.uuid), self.submission_b_archivefile),
                    mock_fileservice_archivefile_post_response(dbmi_settings.FILESERVICE_TOKEN, settings.FILESERVICE_AWS_BUCKET, "submissions_export.zip"),
                    mock_fileservice_download_archivefile_response(dbmi_settings.FILESERVICE_TOKEN),
                    mock_fileservice_uploaded_archivefile_response(dbmi_settings.FILESERVICE_TOKEN),
                    mock_s3_upload_response(settings.FILESERVICE_AWS_BUCKET, "submissions_export.zip"),
                ],
                self.admin_client,
                Method.GET,
                reverse(self.url_pattern, kwargs={
                    "project_key": self.project.project_key,
                }),
                {},
                201,
                "text/html; charset=utf-8",
                True,
                True,
            ),
            RequestResponse(
                "User request",
                [
                    mock_authz_get_permission_response(self.user.jwt, f"Hypatio.{self.project.project_key}"),
                ],
                self.client,
                Method.GET,
                reverse(self.url_pattern, kwargs={
                    "project_key": self.project.project_key,
                }),
                {},
                403,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Anonymous request",
                [],
                self.anonymous_client,
                Method.GET,
                reverse(self.url_pattern, kwargs={
                    "project_key": self.project.project_key,
                }),
                {},
                302,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid project parameter value request",
                [
                    mock_authz_get_permission_response(self.admin.jwt, f"Hypatio.{self.project.project_key}", "MANAGE"),
                ],
                self.admin_client,
                Method.GET,
                reverse(self.url_pattern, kwargs={
                    "project_key": "not-a-project-key",
                }),
                {},
                403,
                "text/html; charset=utf-8",
            ),
        ]

    def test_export_submissions(self):

        # Get request response object
        request_response = next(iter(r for r in self.request_responses if r.successful))

        # Run the request
        request_response.call()

        # Ensure a task was started
        task = Task.objects.first()
        self.assertEqual(task.attempt_count, 1)
        self.assertTrue(task.success)

        # Ensure a challenge task submission export object was created
        export = ChallengeTaskSubmissionExport.objects.first()
        self.assertEqual(self.submissions_export_archivefile["uuid"], str(export.uuid))
        self.assertIn(self.submission_a, export.challenge_task_submissions.all())
        self.assertIn(self.submission_b, export.challenge_task_submissions.all())

        # Ensure an email was sent
        self.assertEqual(len(mail.outbox), 1)


class ManageDownloadSubmissionsExportTestCase(HypatioTestCase):

    # Set the URL pattern for this view.
    url_pattern = "manage:download-submissions-export"

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
        )

        # Setup some submissions
        cls.submission_a = ChallengeTaskSubmission.objects.create(
            uuid=uuid.uuid4(),
            participant=cls.participant,
            challenge_task=cls.challenge_task,
            submission_info='{"test": "Submission A"}',
        )

        cls.submission_a_archivefile = {
            "uuid": str(cls.submission_a),
            "filename": "submission_a.zip",
            "tags": ["test", "submission", "a"],
        }

        # Setup some submissions
        cls.submission_b = ChallengeTaskSubmission.objects.create(
            uuid=uuid.uuid4(),
            participant=cls.participant,
            challenge_task=cls.challenge_task,
            submission_info='{"test": "Submission B"}',
        )

        cls.submission_b_archivefile = {
            "uuid": str(cls.submission_b),
            "filename": "submission_b.zip",
            "tags": ["test", "submission", "b"],
        }

        # Setup some submissions
        cls.submission_export = ChallengeTaskSubmissionExport.objects.create(
            uuid=uuid.uuid4(),
            data_project=cls.project,
            requester_id=cls.admin.id,
        )
        cls.submission_export.challenge_task_submissions.add(cls.submission_a)
        cls.submission_export.challenge_task_submissions.add(cls.submission_b)
        cls.submission_export.save()

        cls.submissions_export_archivefile = {
            "uuid": str(cls.submission_export.uuid),
            "filename": "submissions_export.zip",
            "tags": ["test", "submissions", "export"],
        }

    def setUp(self):
        super().setUp()

        # Set the submission download URL
        self.submission_export_download_url = f"{dbmi_settings.FILESERVICE_URL}/filemaster/api/file/{self.submission_export.uuid}/download/"

        # Set mocks for a successful request
        self.successful_request_mocks = [
            mock_authz_get_permission_response(self.admin.jwt, f"Hypatio.{self.project.project_key}", "MANAGE"),
            mock_fileservice_archivefile_download_response(
                dbmi_settings.FILESERVICE_TOKEN,
                self.submission_export.uuid,
                self.submission_export_download_url,
            ),
        ]

        # Set an invalid ArchiveFile UUID
        self.invalid_archivefile_uuid = uuid.uuid4()

        self.request_responses = [
            RequestResponse(
                "Successful request",
                self.successful_request_mocks,
                self.admin_client,
                Method.GET,
                reverse(self.url_pattern, kwargs={
                    "project_key": self.project.project_key,
                    "fileservice_uuid": self.submission_export.uuid,
                }),
                {},
                200,
                "text/html; charset=utf-8",
                True,
                True,
            ),
            RequestResponse(
                "Invalid project key paramater value request",
                self.successful_request_mocks,
                self.admin_client,
                Method.GET,
                reverse(self.url_pattern, kwargs={
                    "project_key": "not-a-project-key",
                    "fileservice_uuid": self.submission_export.uuid,
                }),
                {},
                403,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Invalid ArchiveFile UUID parameter value request",
                [
                    mock_authz_get_permission_response(self.admin.jwt, f"Hypatio.{self.project.project_key}", "MANAGE"),
                    responses.Response(
                        responses.GET,
                        re.compile(rf"^{dbmi_settings.FILESERVICE_URL}/filemaster/api/file/{self.invalid_archivefile_uuid}/download/?.*$"),
                        status=404,
                        content_type="application/json",
                        match=[responses.matchers.header_matcher({"Authorization": f"Token {dbmi_settings.FILESERVICE_TOKEN}"})],
                    )
                ],
                self.admin_client,
                Method.GET,
                reverse(self.url_pattern, kwargs={
                    "project_key": self.project.project_key,
                    "fileservice_uuid": self.invalid_archivefile_uuid,
                }),
                {},
                404,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "User request",
                [
                    mock_authz_get_permission_response(self.user.jwt, f"Hypatio.{self.project.project_key}"),
                ],
                self.client,
                Method.GET,
                reverse(self.url_pattern, kwargs={
                    "project_key": self.project.project_key,
                    "fileservice_uuid": self.submission_export.uuid,
                }),
                {},
                403,
                "text/html; charset=utf-8",
            ),
            RequestResponse(
                "Anonymous request",
                [],
                self.anonymous_client,
                Method.GET,
                reverse(self.url_pattern, kwargs={
                    "project_key": self.project.project_key,
                    "fileservice_uuid": self.submission_export.uuid,
                }),
                {},
                302,
                "text/html; charset=utf-8",
            ),
        ]

    def test_download_submissions_export(self):

        # Get request response object
        request_response = next(iter(r for r in self.request_responses if r.successful))

        # Run the request
        response = request_response.call()

        # Build what the redirect URL should be
        protocol = urlparse(self.submission_export_download_url).scheme
        path = quote_plus(self.submission_export_download_url.replace(protocol + "://", ""))
        redirect_url = "/proxy/" + protocol + "/" + path

        # Compare
        self.assertEqual(response['X-Accel-Redirect'], redirect_url)


class ManageHostSubmissionTestCase(HypatioTestCase):

    # Set the URL pattern for this view.
    url_pattern = "manage:host-submission"

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
        )

        # Setup some submissions
        cls.submission_a = ChallengeTaskSubmission.objects.create(
            uuid=uuid.uuid4(),
            participant=cls.participant,
            challenge_task=cls.challenge_task,
            submission_info='{"test": "Submission A"}',
        )

        cls.submission_a_archivefile = {
            "uuid": str(cls.submission_a),
            "filename": "submission_a.zip",
            "tags": ["test", "submission", "a"],
            "locations": [
                {
                    "url": f"s3://{settings.FILESERVICE_AWS_BUCKET}/some/random/key/submission_a.zip",
                },
            ],
        }

    def setUp(self):
        super().setUp()

        self.request_responses = [
            RequestResponse(
                "Successful GET request",
                [
                    mock_authz_get_permission_response(self.admin.jwt, f"Hypatio.{self.project.project_key}", "MANAGE")
                ],
                self.admin_client,
                Method.GET,
                reverse(self.url_pattern, kwargs={
                    "fileservice_uuid": self.submission_a.uuid,
                }),
                {},
                200,
                "text/html; charset=utf-8",
                True,
                True,
            ),
            RequestResponse(
                "Successful POST request",
                [
                    mock_authz_get_permission_response(self.admin.jwt, f"Hypatio.{self.project.project_key}", "MANAGE"),
                    mock_fileservice_get_archivefile_response(dbmi_settings.FILESERVICE_TOKEN, str(self.submission_a.uuid), self.submission_a_archivefile),
                ],
                self.admin_client,
                Method.POST,
                reverse(self.url_pattern, kwargs={
                    "fileservice_uuid": self.submission_a.uuid,
                }),
                {
                    "project": self.project.id,
                    "long_name": "Submission A Hosted",
                    "file_name": "some-random-file-name.zip",
                    "file_location": f"{self.project.project_key}/hosted_files"
                },
                200,
                "text/html; charset=utf-8",
                True,
                True,
            ),
            RequestResponse(
                "Invalid project parameter request",
                [
                    mock_authz_get_permission_response(self.admin.jwt, f"Hypatio.{self.project.project_key}", "MANAGE"),
                ],
                self.admin_client,
                Method.POST,
                reverse(self.url_pattern, kwargs={
                    "fileservice_uuid": self.submission_a.uuid,
                }),
                {
                    "project": 9999,
                    "long_name": "Submission A Hosted",
                    "file_name": "some-random-file-name.zip",
                    "file_location": f"{self.project.project_key}/hosted_files"
                },
                400,
                "text/html; charset=utf-8",
                True,
            ),
            RequestResponse(
                "User request",
                [
                    mock_authz_get_permission_response(self.user.jwt, f"Hypatio.{self.project.project_key}"),
                ],
                self.client,
                Method.GET,
                reverse(self.url_pattern, kwargs={
                    "fileservice_uuid": self.submission_a.uuid,
                }),
                {},
                403,
                "text/html; charset=utf-8",
                True,
            ),
            RequestResponse(
                "Anonymous request",
                [
                ],
                self.anonymous_client,
                Method.GET,
                reverse(self.url_pattern, kwargs={
                    "fileservice_uuid": self.submission_a.uuid,
                }),
                {},
                302,
                "text/html; charset=utf-8",
                True,
            ),
            RequestResponse(
                "Invalid parameter value request",
                [
                    mock_authz_get_permission_response(self.admin.jwt, f"Hypatio.{self.project.project_key}", "MANAGE")
                ],
                self.admin_client,
                Method.GET,
                reverse(self.url_pattern, kwargs={
                    "fileservice_uuid": str(uuid.uuid4()),
                }),
                {},
                404,
                "text/html; charset=utf-8",
                True,
            ),
        ]

    def test_authorization(self):

        # Iterate request/response objects
        for request_response in self.request_responses:
            with self.subTest(msg=request_response.name, request_response=request_response):

                # Setup a mock on the S3 copy object operation
                with patch("botocore.client.BaseClient._make_api_call"):

                    # Call it
                    response = request_response.call()

                    # Make assertions
                    self.assertEqual(response.status_code, request_response.status_code)

    def test_status_code(self):

        # Iterate request/response objects
        for request_response in self.request_responses:
            with self.subTest(msg=request_response.name, request_response=request_response):

                # Setup a mock on the S3 copy object operation
                with patch("botocore.client.BaseClient._make_api_call"):

                    # Call it
                    response = request_response.call()

                    # Make assertions
                    self.assertEqual(response.status_code, request_response.status_code)

    def test_content_type(self):

        # Iterate request/response objects
        for request_response in self.request_responses:
            with self.subTest(msg=request_response.name, request_response=request_response):

                # Setup a mock on the S3 copy object operation
                with patch("botocore.client.BaseClient._make_api_call"):

                    # Call it
                    response = request_response.call()

                    # Make assertions
                    self.assertEqual(response["Content-Type"], request_response.content_type)

    def test_get_host_submission(self):

        # Get request response object
        request_response = next(iter(r for r in self.request_responses if r.successful and r.method is Method.GET))

        # Make the call
        response = request_response.call()

        # Check assertions
        self.assertEqual(response.status_code, request_response.status_code)

        # Check that the response contains a rendered HTML template
        self.assertTemplateUsed(response, 'manage/host-submission-form.html')

    def test_post_host_submission(self):

        # Get request response object
        request_response = next(iter(r for r in self.request_responses if r.successful and r.method is Method.POST))

        # Setup a mock on the S3 copy object operation
        with patch("botocore.client.BaseClient._make_api_call"):

            # Make the call
            response = request_response.call()

            # Check assertions
            self.assertEqual(response.status_code, request_response.status_code)
            self.assertEqual(response.content, b"File updated.")

    def test_post_host_submission_invalid_project(self):

        # Get request response object
        request_response = next(iter(r for r in self.request_responses if not r.successful and r.method is Method.POST))

        # Setup a mock on the S3 copy object operation
        with patch("botocore.client.BaseClient._make_api_call"):

            # Make the call
            response = request_response.call()

            # Check assertions
            self.assertEqual(response.status_code, request_response.status_code)
            self.assertNotEqual(response.content, b"File updated.")


class ManageDownloadEmailListTestCase(HypatioTestCase):

    # Set the URL pattern for this view.
    url_pattern = "manage:download-email-list"

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

        # Set the necessary mocks for a normal request/response
        self.successful_request_mocks = [
            mock_authz_get_permission_response(self.admin.jwt, f"Hypatio.{self.project.project_key}", "MANAGE"),
            mock_reg_get_names_response(
                self.admin.jwt,
                {
                    self.user.email: {
                        "first_name": self.user.first_name,
                        "last_name": self.user.last_name,
                    },
                    self.participant_a.user.email: {
                        "first_name": self.participant_a.user.first_name,
                        "last_name": self.participant_a.user.last_name,
                    },
                    self.participant_b.user.email: {
                        "first_name": self.participant_b.user.first_name,
                        "last_name": self.participant_b.user.last_name,
                    }
                }
            ),
        ]

        # Set the URL to change project details.
        url = reverse(self.url_pattern)

        self.request_responses = [
            RequestResponse(
                "Successful request",
                self.successful_request_mocks,
                self.admin_client,
                Method.GET,
                url,
                {
                    "project": self.project.project_key,
                },
                200,
                "text/plain",
                True,
                True,
            ),
            RequestResponse(
                "User request",
                [
                    mock_authz_get_permission_response(self.user.jwt, f"Hypatio.{self.project.project_key}"),
                ],
                self.client,
                Method.GET,
                url,
                {
                    "project": self.project.project_key,
                },
                403,
                "text/html; charset=utf-8",
                True,
            ),
            RequestResponse(
                "Anonymous request",
                [
                ],
                self.anonymous_client,
                Method.GET,
                url,
                {
                    "project": self.project.project_key,
                },
                302,
                "text/html; charset=utf-8",
                True,
            ),
            RequestResponse(
                "Invalid parameter key request",
                self.successful_request_mocks,
                self.admin_client,
                Method.GET,
                url,
                {
                    "project-key": self.project.project_key,
                },
                400,
                "text/html; charset=utf-8",
                True,
            ),
            RequestResponse(
                "Invalid parameter value request",
                self.successful_request_mocks,
                self.admin_client,
                Method.GET,
                url,
                {
                    "project": "not-a-project-key",
                },
                404,
                "text/html; charset=utf-8",
                True,
            ),
        ]

    def test_download_email_list(self):

        # Get the successul request
        request_response = next(iter([r for r in self.request_responses if r.successful]))

        # Run it
        response = request_response.call()

        # List is a plaintext list of "{email} {first_name} {last_name}"
        email_list = [line for line in response.content.decode().splitlines()]

        # Check results
        self.assertIn(f"{self.user.email} {self.user.first_name} {self.user.last_name}", email_list)
        self.assertIn(f"{self.participant_b.user.email} {self.participant_b.user.first_name} {self.participant_b.user.last_name}", email_list)


class ManageRemoveViewPermissionTestCase(HypatioTestCase):

    # Set the URL pattern for this view.
    url_pattern = "manage:remove-view-permission"

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
            permission='VIEW',
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
            permission='VIEW',
        )

    def setUp(self):
        super().setUp()

        self.request_responses = [
            RequestResponse(
                "Successful request",
                [
                    mock_authz_get_permission_response(self.admin.jwt, f"Hypatio.{self.project.project_key}", "MANAGE"),
                    mock_authz_remove_permission_response(self.admin.jwt),
                ],
                self.admin_client,
                Method.GET,
                reverse(self.url_pattern, kwargs={
                    "project_key": self.project.project_key,
                    "user_email": self.participant_b.user.email,
                }),
                {},
                200,
                "text/html; charset=utf-8",
                True,
                True,
            ),
            RequestResponse(
                "User request",
                [
                    mock_authz_get_permission_response(self.user.jwt, f"Hypatio.{self.project.project_key}"),
                ],
                self.client,
                Method.GET,
                reverse(self.url_pattern, kwargs={
                    "project_key": self.project.project_key,
                    "user_email": self.participant_b.user.email,
                }),
                {},
                403,
                "text/html; charset=utf-8",
                True,
            ),
            RequestResponse(
                "Anonymous request",
                [
                ],
                self.anonymous_client,
                Method.GET,
                reverse(self.url_pattern, kwargs={
                    "project_key": self.project.project_key,
                    "user_email": self.participant_b.user.email,
                }),
                {},
                302,
                "text/html; charset=utf-8",
                True,
            ),
            RequestResponse(
                "Invalid parameter value request",
                [
                    mock_authz_get_permission_response(self.admin.jwt, f"Hypatio.{self.project.project_key}", "MANAGE"),
                ],
                self.admin_client,
                Method.GET,
                reverse(self.url_pattern, kwargs={
                    "project_key": "not-a-project-key",
                    "user_email": self.participant_b.user.email,
                }),
                {},
                404,
                "text/html; charset=utf-8",
                True,
            ),
            RequestResponse(
                "Failed AuthZ operation request",
                [
                    mock_authz_get_permission_response(self.admin.jwt, f"Hypatio.{self.project.project_key}", "MANAGE"),
                    mock_authz_remove_permission_response(self.admin.jwt, status_code=500),
                ],
                self.admin_client,
                Method.GET,
                reverse(self.url_pattern, kwargs={
                    "project_key": self.project.project_key,
                    "user_email": self.participant_b.user.email,
                }),
                {},
                200,
                "text/html; charset=utf-8",
                True,
            ),
        ]

    def test_remove_view_permission(self):

        # Get the successul request
        request_response = next(iter([r for r in self.request_responses if r.successful]))

        # Run it
        request_response.call()

        # Make Assertions
        self.assertEqual(Participant.objects.get(user__email=self.participant_a.user.email).permission, "VIEW")
        self.assertNotEqual(Participant.objects.get(user__email=self.participant_b.user.email).permission, "VIEW")
