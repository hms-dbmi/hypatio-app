from django.conf.urls import url, include
from django.contrib import admin
from django.views.defaults import page_not_found

urlpatterns = [
    url(r'^dataprojects/admin/login/', page_not_found, {'exception': Exception('Admin form login disabled.')}),
    url(r'^admin/', admin.site.urls),
    url(r'^contact/', include('contact.urls')),
    url(r'^dataprojects/', include('dataprojects.urls')),
    url(r'^profiles/', include('profiles.urls')),
    url(r'^', include('dataprojects.urls')),
]
