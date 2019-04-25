from django.conf.urls import include
from django.conf.urls import url
from django.contrib import admin

from hypatio.views import index
from projects.views import list_data_projects
from projects.views import list_data_challenges


urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^contact/', include('contact.urls', namespace='contact')),
    url(r'^manage/', include('manage.urls', namespace='manage')),
    url(r'^projects/', include('projects.urls', namespace='projects')),
    url(r'^profile/', include('profile.urls', namespace='profile')),
    url(r'^data-sets/$', list_data_projects, name='data-sets'),
    url(r'^data-challenges/$', list_data_challenges, name='data-challenges'),
    url(r'^healthcheck/?', include('health_check.urls')),
    url(r'^', index, name='index'),
]
