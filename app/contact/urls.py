from django.conf.urls import url
from .views import ContactView

app_name = 'contact'
urlpatterns = (
    url(r'^(?P<project_key>[^/]+)/$', ContactView.as_view(), name='contact_form'),
    url(r'^', ContactView.as_view(), name='contact_form'),
)
