from django import template
from django.conf import settings

import os
import furl

from django.utils.safestring import mark_safe

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

@register.filter
def keyvalue(passed_dictionary, key):
    return passed_dictionary[key]

@register.filter
def keyvalue_permission_scheme(passed_dictionary, key):
    return passed_dictionary[key]['permission_scheme']

@register.filter
def permission_requested(dictionary, project_key):
    return project_key in dictionary

@register.filter
def is_request_granted(dictionary, project_key):
    return dictionary[project_key]['request_granted']

@register.filter
def get_date_requested(dictionary, project_key):
    return dictionary[project_key]["date_requested"]

@register.simple_tag
def modal_contact_form_button(text='Contact us', classes='btn btn-primary btn-md'):

    return mark_safe("""
        <button class='contact-form-button {}'>{}</button>
    """.format(classes, text))


@register.simple_tag
def modal_contact_form_link(text='Contact us', classes=''):

    return mark_safe("""
        <a href=# class='contact-form-button {}'>{}</a>
    """.format(classes, text))