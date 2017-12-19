import os

import mock
from mock import patch, Mock

from django.test import TestCase
from django.conf import settings
from django.core.management import call_command
from django.http import HttpResponse, HttpRequest
from django.contrib.auth import get_user_model

from .models import DataUseAgreement
from .views import submit_request

TEST_JWT_TOKEN = "WIUHDI&WHQDBKbIYWGD^GUQG^DG&wdydwg^@@Ejdh37364BQWKDBKWDU##B@@9wUDBi&@GiYWBD"
TEST_USER_EMAIL = "test-user@example.com"

class HypatioTests(TestCase):

    def setUp(self):
        # Get the fixtures inserted
        call_command("loaddata", 'dataprojects', app_label='dataprojects')

        self.user = get_user_model().objects.create(email=TEST_USER_EMAIL, username=TEST_USER_EMAIL)
        self.user.save()

    def test_every_dua_form_file_exists(self):
        """
        Tests that every Data Use Agreement's agreement_form_file actually exists in our application.
        This is important because right now there is no enforcement between the value entered in this
        field and the existence of such a file on our server.
        """

        data_use_agreements = DataUseAgreement.objects.all()

        for dua in data_use_agreements:
            form_path = os.path.join(settings.DATA_USE_AGREEMENT_FORM_DIR, dua.agreement_form_file)
            self.assertEqual(True, os.path.isfile(form_path), "DUA '" + dua.name + "' agreement_form_file '" + dua.agreement_form_file + "' missing in directory " + settings.DATA_USE_AGREEMENT_FORM_DIR + ".")
