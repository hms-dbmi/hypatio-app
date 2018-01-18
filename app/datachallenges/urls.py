from django.conf.urls import url
from .views import list_data_challenges, signout, manage_contests, grant_access_with_view_permissions

urlpatterns = (
    url(r'^$', list_data_challenges),
    url(r'^grantviewpermissions', grant_access_with_view_permissions),
    url(r'^list/$', list_data_challenges),
    url(r'^managecontests/$', manage_contests),
    url(r'^signout/$', signout),
)
