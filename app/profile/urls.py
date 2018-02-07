from django.conf.urls import url
from .views import update_profile
from .views import profile
from .views import send_confirmation_email_view

urlpatterns = (
    url(r'^$', profile, name='profile'),
    url(r'^send_confirmation_email/$', send_confirmation_email_view),
    url(r'^update', update_profile)
)
