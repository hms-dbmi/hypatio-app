import logging

from pyauth0jwt.auth0authenticate import user_auth_and_jwt

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

from hypatio.sciauthz_services import SciAuthZ

from projects.models import DataProject

# Get an instance of a logger
logger = logging.getLogger(__name__)

@method_decorator(user_auth_and_jwt, name='dispatch')
class DataProjectManageView(TemplateView):
    """
    Builds and renders the screen for special users to manage a DataProject.
    """

    project = None
    template_name = 'manage/base.html'

    def dispatch(self, request, *args, **kwargs):
        """
        Sets up the instance.
        """

        # Get the project key from the URL.
        project_key = self.kwargs['project_key']

        try:
            self.project = DataProject.objects.get(project_key=project_key)
        except ObjectDoesNotExist:
            error_message = "The project you searched for does not exist."
            return render(request, '404.html', {'error_message': error_message})

        user_jwt = request.COOKIES.get("DBMI_JWT", None)

        sciauthz = SciAuthZ(settings.AUTHZ_BASE, user_jwt, request.user.email)
        is_manager = sciauthz.user_has_manage_permission(project_key)

        if not is_manager:
            logger.debug(
                '[HYPATIO][DEBUG][manage_contest] User {email} does not have MANAGE permissions for item {project_key}.'.format(
                    email=request.user.email,
                    project_key=project_key
                )
            )
            return HttpResponse("Unauthorized", status=403)

        return super(DataProjectManageView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """
        Dynamically builds the context for rendering the view based on information
        about the user and the DataProject.
        """

        # Get super's context. This is the dictionary of variables for the base template being rendered.
        context = super(DataProjectManageView, self).get_context_data(**kwargs)

        context['project'] = self.project

        return context
