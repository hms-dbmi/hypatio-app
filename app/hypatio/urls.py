from django.conf.urls import url, include
from django.contrib import admin
from django.views.defaults import page_not_found
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^contact/', include('contact.urls')),
    url(r'^projects/', include('projects.urls')),
    url(r'^profile/', include('profile.urls')),
    url(r'^', include('projects.urls')),
]