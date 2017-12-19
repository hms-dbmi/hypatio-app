from django import template
from django.utils.safestring import mark_safe
from dataprojects.models import DataUseAgreement
from django.conf import settings

from os.path import normpath, join
import os

register = template.Library()

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

@register.filter
def get_dua_form_file_contents(dua_form_file):

    form_path = os.path.join(settings.DATA_USE_AGREEMENT_FORM_DIR, dua_form_file)
    return open(form_path, 'r').read()
