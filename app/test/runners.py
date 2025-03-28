import os
import mock

from django.test.runner import DiscoverRunner
from django.core.management.utils import get_random_secret_key

class HypatioTestRunner(DiscoverRunner):

    def setup_databases(self, **kwargs):
        with mock.patch("hypatio.file_services.check_groups", return_value=True):
            return super().setup_databases(**kwargs)
