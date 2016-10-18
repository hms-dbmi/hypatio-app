from django.conf.urls import url
from .views import listDataprojects

urlpatterns = (
    url(r'^list/$', listDataprojects),
)
