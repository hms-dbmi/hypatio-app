from django.conf.urls import url
from .views import listDataprojects, request_access, submit_request

urlpatterns = (
    url(r'^$', listDataprojects),
    url(r'^list/$', listDataprojects),
    url(r'^request_access/$', request_access),
    url(r'^submit_request/$', submit_request),
)
