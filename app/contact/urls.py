from django.conf.urls import url
from .views import contact_form

urlpatterns = (
    url(r'^', contact_form, name='contact_form'),
)
