from django.conf.urls import url

from manage.apps import ManageConfig
from manage.views import DataProjectListManageView
from manage.views import DataProjectManageView
from manage.views import manage_team
from manage.views import ProjectParticipants
from manage.views import team_notification

from manage.api import set_dataproject_details
from manage.api import set_dataproject_registration_status
from manage.api import set_dataproject_visible_status
from manage.api import get_static_agreement_form_html
from manage.api import get_hosted_file_edit_form
from manage.api import process_hosted_file_edit_form_submission
from manage.api import download_signed_form
from manage.api import change_signed_form_status
from manage.api import get_signed_form_status
from manage.api import save_team_comment
from manage.api import set_team_status
from manage.api import delete_team
from manage.api import download_submission
from manage.api import host_submission
from manage.api import download_team_submissions
from manage.api import download_email_list
from manage.api import get_hosted_file_logs
from manage.api import grant_view_permission
from manage.api import remove_view_permission
from manage.api import sync_view_permissions
from manage.api import export_submissions
from manage.api import download_submissions_export
from manage.api import delete_submissions_export

app_name = ManageConfig.name

urlpatterns = [
    url(r'^$', DataProjectListManageView.as_view(), name='manage-projects'),
    url(r'^download-email-list/$', download_email_list, name='download-email-list'),
    url(r'^set-dataproject-details/$', set_dataproject_details, name='set-dataproject-details'),
    url(r'^set-dataproject-registration-status/$', set_dataproject_registration_status, name='set-dataproject-registration-status'),
    url(r'^set-dataproject-visible-status/$', set_dataproject_visible_status, name='set-dataproject-visible-status'),
    url(r'^get-static-agreement-form-html/$', get_static_agreement_form_html, name='get-static-agreement-form-html'),
    url(r'^get-hosted-file-edit-form/$', get_hosted_file_edit_form, name='get-hosted-file-edit-form'),
    url(r'^get-hosted-file-logs/$', get_hosted_file_logs, name='get-hosted-file-logs'),
    url(r'^process-hosted-file-edit-form-submission/$', process_hosted_file_edit_form_submission, name='process-hosted-file-edit-form-submission'),
    url(r'^download-signed-form/$', download_signed_form, name='download-signed-form'),
    url(r'^get-signed-form-status/$', get_signed_form_status, name='get-signed-form-status'),
    url(r'^change-signed-form-status/$', change_signed_form_status, name='change-signed-form-status'),
    url(r'^save-team-comment/$', save_team_comment, name='save-team-comment'),
    url(r'^set-team-status/$', set_team_status, name='set-team-status'),
    url(r'^delete-team/$', delete_team, name='delete-team'),
    url(r'^team-notification/$', team_notification, name='team-notification'),
    url(r'^download-team-submissions/(?P<project_key>[^/]+)/(?P<team_leader_email>[^/]+)/$', download_team_submissions, name='download-team-submissions'),
    url(r'^download-submission/(?P<fileservice_uuid>[^/]+)/$', download_submission, name='download-submission'),
    url(r'^export-submissions/(?P<project_key>[^/]+)/$', export_submissions, name='export-submissions'),
    url(r'^download-submissions-export/(?P<project_key>[^/]+)/(?P<fileservice_uuid>[^/]+)/$', download_submissions_export, name='download-submissions-export'),
    url(r'^delete-submissions-export/(?P<project_key>[^/]+)/(?P<fileservice_uuid>[^/]+)/$', delete_submissions_export, name='delete-submissions-export'),
    url(r'^host-submission/(?P<fileservice_uuid>[^/]+)/$', host_submission, name='host-submission'),
    url(r'^sync-view-permissions/(?P<project_key>[^/]+)/$', sync_view_permissions, name='sync-view-permissions'),
    url(r'^grant-view-permission/(?P<project_key>[^/]+)/(?P<user_email>[^/]+)/$', grant_view_permission, name='grant-view-permission'),
    url(r'^remove-view-permission/(?P<project_key>[^/]+)/(?P<user_email>[^/]+)/$', remove_view_permission, name='remove-view-permission'),
    url(r'^get-project-participants/(?P<project_key>[^/]+)/$', ProjectParticipants.as_view(), name='get-project-participants'),
    url(r'^(?P<project_key>[^/]+)/$', DataProjectManageView.as_view(), name='manage-project'),
    url(r'^(?P<project_key>[^/]+)/(?P<team_leader>[^/]+)/$', manage_team, name='manage-team'),
]
