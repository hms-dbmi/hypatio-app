from django import template
from django.conf import settings

register = template.Library()

@register.simple_tag
def get_recaptcha_client_id():

    return settings.RECAPTCHA_CLIENT_ID
