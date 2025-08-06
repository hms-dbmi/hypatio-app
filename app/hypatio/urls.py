from django.urls import include
from django.urls import re_path
from django.contrib import admin

from hypatio.views import index
from projects.views import list_data_projects
from projects.views import list_data_challenges
from projects.views import list_software_projects
from projects.views import GroupView
from hypatio.api import CSPReportView


urlpatterns = [
    re_path(r'^admin/', admin.site.urls),
    re_path(r'^contact/', include('contact.urls', namespace='contact')),
    re_path(r'^manage/', include('manage.urls', namespace='manage')),
    re_path(r'^projects/', include('projects.urls', namespace='projects')),
    re_path(r'^profile/', include('profile.urls', namespace='profile')),
    re_path(r'^data-sets/$', list_data_projects, name='data-sets'),
    re_path(r'^data-challenges/$', list_data_challenges, name='data-challenges'),
    re_path(r'^software-projects/$', list_software_projects, name='software-projects'),
    re_path(r'^healthcheck/?', include('health_check.urls')),
    re_path(r'^groups/(?P<group_key>[^/]+)/?$', GroupView.as_view(), name="group"),
    re_path(r'^workflows/', include('workflows.urls', namespace='workflows')),
    re_path(r'csp-report/', CSPReportView.as_view(), name="csp-report"),
    re_path(r'^/?$', index, name='index'),
]
