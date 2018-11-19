from django.conf.urls import url

from manage.views import DataProjectListManageView
from manage.views import DataProjectManageView
from manage.views import manage_team

from manage.api import set_dataproject_details
from manage.api import set_dataproject_registration_status
from manage.api import set_dataproject_visible_status
from manage.api import get_static_agreement_form_html
from manage.api import get_hosted_file_edit_form
from manage.api import process_hosted_file_edit_form_submission
from manage.api import download_signed_form
from manage.api import change_signed_form_status
from manage.api import save_team_comment
from manage.api import set_team_status
from manage.api import delete_team
from manage.api import download_team_submissions
from manage.api import download_email_list

app_name = 'manage'
urlpatterns = [
    url(r'^$', DataProjectListManageView.as_view(), name='manage-projects'),
    url(r'^download-email-list/$', download_email_list),
    url(r'^set-dataproject-details', set_dataproject_details, name='set-dataproject-details'),
    url(r'^set-dataproject-registration-status', set_dataproject_registration_status, name='set-dataproject-registration-status'),
    url(r'^set-dataproject-visible-status', set_dataproject_visible_status, name='set-dataproject-visible-status'),
    url(r'^get-static-agreement-form-html', get_static_agreement_form_html, name='get-static-agreement-form-html'),
    url(r'^get-hosted-file-edit-form', get_hosted_file_edit_form, name='get-hosted-file-edit-form'),
    url(r'^process-hosted-file-edit-form-submission', process_hosted_file_edit_form_submission, name='process-hosted-file-edit-form-submission'),
    url(r'^download-signed-form/$', download_signed_form, name='download-signed-form'),
    url(r'^change-signed-form-status/$', change_signed_form_status, name='change-signed-form-status'),
    url(r'^save-team-comment/$', save_team_comment, name='save-team-comment'),
    url(r'^set-team-status/$', set_team_status, name='set-team-status'),
    url(r'^delete-team/$', delete_team, name='delete-team'),
    url(r'^download-team-submissions/$', download_team_submissions, name='download-team-submissions'),
    url(r'^(?P<project_key>[^/]+)/$', DataProjectManageView.as_view(), name='manage-project'),
    url(r'^(?P<project_key>[^/]+)/(?P<team_leader>[^/]+)/$', manage_team),
]
