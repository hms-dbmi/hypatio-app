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

    # Pass the current URI to SciAuth, which it will use to redirect users who verify their emails
    login_url.args.add('email_confirm_success_url', current_uri)

    return login_url.url
