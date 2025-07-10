from django.urls import re_path, path, include
from rest_framework import routers

from manage.apps import ManageConfig
from manage.views import DataProjectListManageView
from manage.views import DataProjectManageView
from manage.views import manage_team
from manage.views import ProjectParticipants
from manage.views import ProjectPendingParticipants
from manage.views import team_notification
from manage.views import UploadSignedAgreementFormView
from manage.views import UploadSignedAgreementFormFileView
from manage.views import ProjectDataUseReportParticipants
from manage.views import WorkflowStateView

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
from manage.api import DataProjectWorkflowStateViewSet
from manage.api import DataProjectFileViewSet

app_name = ManageConfig.name

router = routers.SimpleRouter()
router.register(r'(?P<data_project_key>[^/]+)/workflow-state', DataProjectWorkflowStateViewSet, basename='dataproject-workflow-state')
router.register(r'(?P<data_project_key>[^/]+)/file', DataProjectFileViewSet, basename='dataproject-file')

urlpatterns = [
    re_path(r'^$', DataProjectListManageView.as_view(), name='manage-projects'),
    re_path(r'^download-email-list/$', download_email_list, name='download-email-list'),
    re_path(r'^set-dataproject-details/$', set_dataproject_details, name='set-dataproject-details'),
    re_path(r'^set-dataproject-registration-status/$', set_dataproject_registration_status, name='set-dataproject-registration-status'),
    re_path(r'^set-dataproject-visible-status/$', set_dataproject_visible_status, name='set-dataproject-visible-status'),
    re_path(r'^get-static-agreement-form-html/$', get_static_agreement_form_html, name='get-static-agreement-form-html'),
    re_path(r'^get-hosted-file-edit-form/$', get_hosted_file_edit_form, name='get-hosted-file-edit-form'),
    re_path(r'^get-hosted-file-logs/$', get_hosted_file_logs, name='get-hosted-file-logs'),
    re_path(r'^process-hosted-file-edit-form-submission/$', process_hosted_file_edit_form_submission, name='process-hosted-file-edit-form-submission'),
    re_path(r'^download-signed-form/$', download_signed_form, name='download-signed-form'),
    re_path(r'^get-signed-form-status/$', get_signed_form_status, name='get-signed-form-status'),
    re_path(r'^change-signed-form-status/$', change_signed_form_status, name='change-signed-form-status'),
    re_path(r'^save-team-comment/$', save_team_comment, name='save-team-comment'),
    re_path(r'^set-team-status/$', set_team_status, name='set-team-status'),
    re_path(r'^delete-team/$', delete_team, name='delete-team'),
    re_path(r'^team-notification/$', team_notification, name='team-notification'),
    re_path(r'^download-team-submissions/(?P<project_key>[^/]+)/(?P<team_leader_email>[^/]+)/$', download_team_submissions, name='download-team-submissions'),
    re_path(r'^download-submission/(?P<fileservice_uuid>[^/]+)/$', download_submission, name='download-submission'),
    re_path(r'^export-submissions/(?P<project_key>[^/]+)/$', export_submissions, name='export-submissions'),
    re_path(r'^download-submissions-export/(?P<project_key>[^/]+)/(?P<fileservice_uuid>[^/]+)/$', download_submissions_export, name='download-submissions-export'),
    re_path(r'^host-submission/(?P<fileservice_uuid>[^/]+)/$', host_submission, name='host-submission'),
    re_path(r'^sync-view-permissions/(?P<project_key>[^/]+)/$', sync_view_permissions, name='sync-view-permissions'),
    re_path(r'^grant-view-permission/(?P<project_key>[^/]+)/(?P<user_email>[^/]+)/$', grant_view_permission, name='grant-view-permission'),
    re_path(r'^remove-view-permission/(?P<project_key>[^/]+)/(?P<user_email>[^/]+)/$', remove_view_permission, name='remove-view-permission'),
    re_path(r'^get-project-participants/(?P<project_key>[^/]+)/$', ProjectParticipants.as_view(), name='get-project-participants'),
    re_path(r'^get-project-pending-participants/(?P<project_key>[^/]+)/$', ProjectPendingParticipants.as_view(), name='get-project-pending-participants'),
    re_path(r'^get-project-data-use-reporting-participants/(?P<project_key>[^/]+)/$', ProjectDataUseReportParticipants.as_view(), name='get-project-data-use-reporting-participants'),
    re_path(r'^upload-signed-agreement-form/(?P<project_key>[^/]+)/(?P<user_email>[^/]+)/$', UploadSignedAgreementFormView.as_view(), name='upload-signed-agreement-form'),
    re_path(r'^upload-signed-agreement-form-file/(?P<signed_agreement_form_id>[^/]+)/$', UploadSignedAgreementFormFileView.as_view(), name='upload-signed-agreement-form-file'),
    re_path(r'^workflow/(?P<workflow_state_id>[^/]+)/$', WorkflowStateView.as_view(), name='workflow-state'),
    path('', include(router.urls)),
    re_path(r'^(?P<project_key>[^/]+)/$', DataProjectManageView.as_view(), name='manage-project'),
    re_path(r'^(?P<project_key>[^/]+)/(?P<team_leader>[^/]+)/$', manage_team, name='manage-team'),
]
