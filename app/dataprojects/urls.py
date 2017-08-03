from django.conf.urls import url
from .views import listDataprojects, request_access, submit_request, signout, contact_form

urlpatterns = (
    url(r'^$', listDataprojects),
    url(r'^list/$', listDataprojects),
    url(r'^request_access/$', request_access),
    url(r'^submit_request/$', submit_request),
    url(r'^signout/$', signout),
    url(r'^contact_form/$', contact_form, name='contact_form'),
)
