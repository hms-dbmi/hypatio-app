
from django.shortcuts import render
from django.utils.functional import SimpleLazyObject
from django.urls import resolve, Resolver404

from hypatio.auth0authenticate import public_user_auth_and_jwt
from projects.apps import ProjectsConfig
from projects.models import Group, DataProject

import logging
logger = logging.getLogger(__name__)


@public_user_auth_and_jwt
def index(request, template_name='index.html'):
    """
    Homepage for the DBMI Portal
    """

    context = {}

    return render(request, template_name, context=context)

def navigation_context(request):
    """
    Includes global navigation context in all requests.

    This method is enabled by including it in settings.TEMPLATES as
    a context processor.

    :param request: The current HttpRequest
    :type request: HttpRequest
    :return: The context that should be included in the response's context
    :rtype: dict
    """
    def group_context():

        # Check for an active project and determine its group
        groups = Group.objects.filter(dataproject__isnull=False, dataproject__visible=True).distinct()
        active_group = None

        # Attempt to resolve the current URL
        try:
            match = resolve(request.path)
            
            # Check if projects
            if match and match.app_name == ProjectsConfig.name and "project_key" in match.kwargs:
                project = DataProject.objects.filter(project_key=match.kwargs["project_key"]).first()
                if project:

                    # Check for group
                    active_group = next((g for g in groups if project in g.dataproject_set.all()), None)

        except Resolver404:
            logger.debug(f"Path could not be resolved: {request.path}")

        except Exception as e:
            logger.exception(f"Group context error: {e}", exc_info=True)

        # Pull out top-level groups
        parent_groups_keys = groups.filter(parent__isnull=False).values_list('parent', flat=True)
        parent_groups = Group.objects.filter(id__in=parent_groups_keys)

        # Remove groups that will be placed under a parent group
        groups = groups.filter(parent__isnull=True)

        return {
            "parent_groups": parent_groups,
            "groups": groups,
            "active_group": active_group,
        }

    return {
        "navigation": SimpleLazyObject(group_context)
    }
