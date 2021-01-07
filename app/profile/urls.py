from django.conf.urls import url

from profile.views import profile
from profile.views import send_confirmation_email_view
from profile.views import signout
from profile.views import update_profile

app_name = 'profile'
urlpatterns = [
    url(r'^$', profile, name='profile'),
    url(r'^send_confirmation_email/$', send_confirmation_email_view, name='send_confirmation_email'),
    url(r'^update/$', update_profile, name='update'),
    url(r'^signout/$', signout, name='signout'),
]