from django.conf.urls import url
from .views import contact_form

app_name = 'contact'
urlpatterns = (
    url(r'^(?P<project_key>[^/]+)/?$', contact_form, name='contact_form'),
    url(r'^', contact_form, name='contact_form'),
)
