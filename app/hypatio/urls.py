from django.conf import settings
from django.conf.urls import include
from django.conf.urls import url
from django.conf.urls.static import static
from django.contrib import admin
from django.views.defaults import page_not_found

from projects.views import list_data_projects
from projects.views import list_data_challenges

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^contact/', include('contact.urls')),
    url(r'^manage/', include('manage.urls')),
    url(r'^projects/', include('projects.urls')),
    url(r'^profile/', include('profile.urls')),
    url(r'^data-sets/$', list_data_projects),
    url(r'^data-challenges/$', list_data_challenges),
    url(r'^', include('projects.urls')),
]