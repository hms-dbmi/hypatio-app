from django.conf.urls import url
from .views import list_data_challenges, signout

urlpatterns = (
    url(r'^$', list_data_challenges),
    url(r'^list/$', list_data_challenges),
    url(r'^signout/$', signout),
)
