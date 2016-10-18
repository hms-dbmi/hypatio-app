from django.conf.urls import url
from .views import token_login, token_redirect, sso_login, login_done, landing_page


urlpatterns = (
    url(r'^token_login/$', token_login),
    url(r'^tr/$', token_redirect),
    url(r'^sso_login/$', sso_login),
    url(r'^login_done/$', login_done),
    url(r'^landing_page/$', landing_page),
)
