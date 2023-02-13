from django.urls import re_path
from .views import contact_form

app_name = 'contact'
urlpatterns = (
    re_path(r'^(?P<project_key>[^/]+)/?$', contact_form, name='contact_form'),
    re_path(r'^', contact_form, name='contact_form'),
)
