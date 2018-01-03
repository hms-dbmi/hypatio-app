from django.conf.urls import url
from .views import list_data_projects, request_access, submit_request, signout, contact_form

urlpatterns = (
    url(r'^$', list_data_projects),
    url(r'^list/$', list_data_projects),
    url(r'^request_access/$', request_access),
    url(r'^submit_request/$', submit_request),
    url(r'^signout/$', signout),
    url(r'^contact_form/$', contact_form, name='contact_form'),
)
