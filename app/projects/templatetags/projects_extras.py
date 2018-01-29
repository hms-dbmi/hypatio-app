from django import template
# from .models import DataUseAgreement
from django.conf import settings

from os.path import normpath, join
import os

register = template.Library()

@register.filter
def get_agreement_form_file_contents(agreement_form_file_name):

    form_path = os.path.join(settings.MEDIA_ROOT, agreement_form_file_name)
    return open(form_path, 'r').read()
