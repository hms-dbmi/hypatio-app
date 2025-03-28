from django.test import TestCase
from django.test import RequestFactory
from django.test import Client
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import mail
import responses


class HypatioTestCase(TestCase):

    request_responses = []

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        # Get the test authentication
        cls.test_authentication = settings.TEST_AUTH

        # Setup a user
        cls.user = get_user_model().objects.create(
            first_name = "Test",
            last_name = "User",
            username = "test_user@email.com",
            email = "test_user@email.com",
        )
        cls.user.jwt = cls.test_authentication.get_jwt(
            first_name = "Test",
            last_name = "User",
            email = "test_user@email.com",
        )

        # Setup an admin
        cls.admin = get_user_model().objects.create(
            first_name = "Test",
            last_name = "Admin",
            username = "admin@dbmi.hms.harvard.edu",
            email = "admin@dbmi.hms.harvard.edu",
        )
        cls.admin.jwt = cls.test_authentication.get_jwt(
            first_name = "Test",
            last_name = "Admin",
            email = "admin@dbmi.hms.harvard.edu",
        )

    def setUp(self):
        responses.start()
        super().setUp()

        # Create a factory and client.
        self.factory = RequestFactory()
        self.client = Client()
        self.admin_client = Client()
        self.anonymous_client = Client()

        # Login.
        self.client.cookies['DBMI_JWT'] = self.user.jwt
        self.client.force_login(self.user)

        # Login.
        self.admin_client.cookies['DBMI_JWT'] = self.admin.jwt
        self.admin_client.force_login(self.admin)

    def tearDown(self):
        super().tearDown()
        responses.stop()
        responses.reset()

    def test_status_code(self):

        # Iterate request/response objects
        for request_response in self.request_responses:
            with self.subTest(msg=request_response.name, request_response=request_response):

                # Call it
                response = request_response.call()

                # Make assertions
                self.assertEqual(response.status_code, request_response.status_code)

                # Reset mail
                mail.outbox.clear()

    def test_content_type(self):

        # Iterate request/response objects
        for request_response in self.request_responses:
            with self.subTest(msg=request_response.name, request_response=request_response):

                # Call it
                response = request_response.call()

                # Make assertions
                self.assertEqual(response["Content-Type"], request_response.content_type)

                # Reset mail
                mail.outbox.clear()
