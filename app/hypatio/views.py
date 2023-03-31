import os
from django.shortcuts import render
from django.utils.functional import SimpleLazyObject

from hypatio.auth0authenticate import public_user_auth_and_jwt
from projects.models import Group, DataProject

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
        groups = Group.objects.all()
        active_group = None
        project = DataProject.objects.filter(project_key=os.path.basename(os.path.normpath(request.path))).first()
        if project:

            # Check for group
            active_group = next((g for g in groups if project in g.dataproject_set.all()), None)

        return {
            "groups": groups,
            "active_group": active_group,
        }

    return {
        "navigation": SimpleLazyObject(group_context)
    }
