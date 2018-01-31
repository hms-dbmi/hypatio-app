from django.conf.urls import url

from .views import list_data_projects
from .views import list_data_contests
from .views import request_access
from .views import submit_user_permission_request
from .views import manage_contests
from .views import save_signed_agreement_form
from .views import grant_access_with_view_permissions
from .views import project_details
from .views import signout

urlpatterns = (
    url(r'^$', list_data_projects),
    url(r'^list_data_projects/$', list_data_projects),
    url(r'^list_data_contests/$', list_data_contests),
    url(r'^request_access/$', request_access),
    url(r'^submit_user_permission_request/$', submit_user_permission_request),
    url(r'^managecontests/$', manage_contests),
    url(r'^grantviewpermissions', grant_access_with_view_permissions),
    url(r'^save_signed_agreement_form', save_signed_agreement_form),
    url(r'^signout/$', signout),
    url(r'^(?P<project_key>[^/]+)/$', project_details)
)
