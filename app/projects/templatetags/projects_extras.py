from django import template
# from .models import DataUseAgreement
from django.conf import settings

from os.path import normpath, join
import os

register = template.Library()

# @register.filter
# def get_dua_form_file_contents(dua_form_file):

#     form_path = os.path.join(settings.DATA_USE_AGREEMENT_FORM_DIR, dua_form_file)
#     return open(form_path, 'r').read()
