from django.conf.urls import url
from .views import profile

urlpatterns = (
    url(r'^$', profile),
)
