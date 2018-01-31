from django import template
from django.conf import settings
from os.path import normpath
from os.path import join
import os
import furl

register = template.Library()

@register.filter
def get_agreement_form_file_contents(agreement_form_file_name):

    form_path = os.path.join(settings.MEDIA_ROOT, agreement_form_file_name)
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

    # We want email verification by default so pass that success url too
    login_url.args.add('email_confirm_success_url', settings.EMAIL_CONFIRM_SUCCESS_URL)

    return login_url.url
