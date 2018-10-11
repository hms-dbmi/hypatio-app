from django.conf.urls import url

from manage.views import DataProjectManageView
from manage.views import manage_team
from manage.views import download_email_list

from manage.api import set_dataproject_details
from manage.api import set_dataproject_registration_status
from manage.api import set_dataproject_visible_status
from manage.api import get_static_agreement_form_html
from manage.api import get_hosted_file_edit_form
from manage.api import process_hosted_file_edit_form_submission

app_name = 'manage'
urlpatterns = [
    # TODO url(r'^$', LIST_PROJECTS_YOU_MANAGE),
    url(r'^download-email-list/$', download_email_list),
    url(r'^set-dataproject-details', set_dataproject_details, name='set-dataproject-details'),
    url(r'^set-dataproject-registration-status', set_dataproject_registration_status, name='set-dataproject-registration-status'),
    url(r'^set-dataproject-visible-status', set_dataproject_visible_status, name='set-dataproject-visible-status'),
    url(r'^get-static-agreement-form-html', get_static_agreement_form_html, name='get-static-agreement-form-html'),
    url(r'^get-hosted-file-edit-form', get_hosted_file_edit_form, name='get-hosted-file-edit-form'),
    url(r'^process-hosted-file-edit-form-submission', process_hosted_file_edit_form_submission, name='process-hosted-file-edit-form-submission'),
    url(r'^(?P<project_key>[^/]+)/$', DataProjectManageView.as_view(), name='manage-project'),
    url(r'^(?P<project_key>[^/]+)/(?P<team_leader>[^/]+)/$', manage_team),
]
