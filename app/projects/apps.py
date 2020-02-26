from django.apps import AppConfig
from django.db.models.signals import post_migrate

import logging
logger = logging.getLogger(__name__)


def check_fileservice(sender, **kwargs):
    """
    Checks Fileservice to ensure the groups are configured for this service
    """
    from hypatio.file_services import check_groups

    logger.debug('Sources: Checking Fileservice groups')
    if check_groups(request={}):
        logging.info('Sources: Fileservice group was successfully created')
    else:
        logging.error('Sources: Fileservice group could not be created')
        raise SystemError('Fileservice group could not be created')


class ProjectsConfig(AppConfig):
    name = 'projects'

    def ready(self):
        """
        Run any one-time only startup routines here
        """
        # Check Fileservice groups once
        post_migrate.connect(check_fileservice, sender=self)
