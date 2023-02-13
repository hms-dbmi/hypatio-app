from django.urls import re_path

from profile.views import profile
from profile.views import send_confirmation_email_view
from profile.views import signout
from profile.views import update_profile

app_name = 'profile'
urlpatterns = [
    re_path(r'^$', profile, name='profile'),
    re_path(r'^send_confirmation_email/?$', send_confirmation_email_view, name='send_confirmation_email'),
    re_path(r'^update/?$', update_profile, name='update'),
    re_path(r'^signout/?$', signout, name='signout'),
]
