from django.conf.urls import url, include
from django.contrib import admin
from django.views.defaults import page_not_found

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^contact/', include('contact.urls')),
    url(r'^datachallenges/', include('datachallenges.urls')),
    url(r'^dataprojects/', include('dataprojects.urls')),
    url(r'^profile/', include('profile.urls')),
    url(r'^', include('dataprojects.urls')),
]
