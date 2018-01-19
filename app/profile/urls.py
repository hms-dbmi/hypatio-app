from django.conf.urls import url
from .views import profile, send_confirmation_email_view

urlpatterns = (
    url(r'^$', profile),
    url(r'^send_confirmation_email/$', send_confirmation_email_view)
)
