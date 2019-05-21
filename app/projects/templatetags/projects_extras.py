import os
import datetime
import furl
import logging

from django import template
from django.conf import settings
from django.utils.safestring import mark_safe
from django.utils.timezone import utc

from hypatio.sciauthz_services import SciAuthZ

register = template.Library()

# Get an instance of a logger
logger = logging.getLogger(__name__)

@register.filter
def get_html_form_file_contents(form_file_path):

    form_path = os.path.join(settings.STATIC_ROOT, form_file_path)
    return open(form_path, 'r').read()

@register.filter
def get_login_url(current_uri):

    # Build the login URL
    login_url = furl.furl(settings.ACCOUNT_SERVER_URL)

    # Add the next URL
    login_url.args.add('next', current_uri)

    # Add project, if any
    project = getattr(settings, 'PROJECT', None)
    if project is not None:
        login_url.args.add('project', project)

    # Pass the current URI to SciAuth, which it will use to redirect users who verify their emails
    login_url.args.add('email_confirm_success_url', current_uri)

    return login_url.url

@register.simple_tag
def is_hostedfile_currently_enabled(hostedfile):

    # If the file is not marked as enabled, it should not be displayed.
    if not hostedfile.enabled:
        return False

    # If there is an opened and closed time, the current time must be within that window
    if hostedfile.opened_time is not None and hostedfile.closed_time is not None:
        return (datetime.datetime.utcnow().replace(tzinfo=utc) > hostedfile.opened_time) and (datetime.datetime.utcnow().replace(tzinfo=utc) < hostedfile.closed_time)

    if hostedfile.opened_time is not None:
        return datetime.datetime.utcnow().replace(tzinfo=utc) > hostedfile.opened_time

    if hostedfile.closed_time is not None:
        return datetime.datetime.utcnow().replace(tzinfo=utc) < hostedfile.closed_time

    return True

@register.simple_tag
def is_challengetask_currently_enabled(challengetask):

    # If the task is not marked as enabled, it should not be displayed.
    if not challengetask.enabled:
        return False

    # If there is an opened and closed time, the current time must be within that window
    if challengetask.opened_time is not None and challengetask.closed_time is not None:
        return (datetime.datetime.utcnow().replace(tzinfo=utc) > challengetask.opened_time) and (datetime.datetime.utcnow().replace(tzinfo=utc) < challengetask.closed_time)

    if challengetask.opened_time is not None:
        return datetime.datetime.utcnow().replace(tzinfo=utc) > challengetask.opened_time

    if challengetask.closed_time is not None:
        return datetime.datetime.utcnow().replace(tzinfo=utc) < challengetask.closed_time

    return True

@register.simple_tag
def is_project_manager(request):
    """
    Returns True if the user manages any projects.
    """

    user_jwt = request.COOKIES.get("DBMI_JWT", None)
    sciauthz = SciAuthZ(settings.AUTHZ_BASE, user_jwt, request.user.email)
    has_manage_permissions = sciauthz.user_has_any_manage_permissions()

    return has_manage_permissions
