import datetime
from furl import furl
import logging

from django import template
from django.conf import settings
from django.utils.timezone import utc
from django.template.loader import render_to_string
from dbmi_client.authn import login_redirect_url

from hypatio.dbmiauthz_services import DBMIAuthz

register = template.Library()

# Get an instance of a logger
logger = logging.getLogger(__name__)

@register.filter
def get_html_form_file_contents(form_file_path):
    return render_to_string(form_file_path)

@register.simple_tag
def get_agreement_form_template(form_file_path, context={}):
    return render_to_string(form_file_path, context=context)

@register.filter
def get_login_url(current_uri):

    # Build the login URL
    login_url = furl(login_redirect_url(None, next_url=current_uri))

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


@register.simple_tag(takes_context=True)
def is_project_manager(context, request):
    """
    Returns True if the user manages any projects.
    """
    # Check existing context for 'has_manage_permission'
    if context.get('has_manage_permissions'):
        return True

    return DBMIAuthz.user_has_any_manage_permissions(request=request)
