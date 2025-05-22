from django.urls import re_path

from projects.apps import ProjectsConfig
from projects.views import list_data_projects
from projects.views import data_use_report
from projects.views import signed_agreement_form
from projects.views import DataProjectView

from projects.api import join_team
from projects.api import leave_team
from projects.api import create_team
from projects.api import approve_team_join
from projects.api import reject_team_join
from projects.api import finalize_team
from projects.api import download_dataset
from projects.api import upload_challengetasksubmission_file
from projects.api import delete_challengetasksubmission
from projects.api import save_signed_agreement_form
from projects.api import save_signed_external_agreement_form
from projects.api import submit_user_permission_request
from projects.api import upload_signed_agreement_form
from projects.api import HostedFileSetAutocomplete
from projects.api import update_institutional_members
from projects.views import qualtrics

app_name = ProjectsConfig.name

urlpatterns = [
    re_path(r'^$', list_data_projects, name='index'),
    re_path(r'^autocomplete/hostedfileset/$', HostedFileSetAutocomplete.as_view(create_field='title'), name='hostedfileset-autocomplete'),
    re_path(r'^submit_user_permission_request/$', submit_user_permission_request, name='submit_user_permission_request'),
    re_path(r'^save_signed_agreement_form', save_signed_agreement_form, name='save_signed_agreement_form'),
    re_path(r'^save_signed_external_agreement_form', save_signed_external_agreement_form, name='save_signed_external_agreement_form'),
    re_path(r'^upload_signed_agreement_form', upload_signed_agreement_form, name='upload_signed_agreement_form'),
    re_path(r'^join_team/$', join_team, name='join_team'),
    re_path(r'^leave_team/$', leave_team, name='leave_team'),
    re_path(r'^approve_team_join/$', approve_team_join, name='approve_team_join'),
    re_path(r'^reject_team_join/$', reject_team_join, name='reject_team_join'),
    re_path(r'^create_team/$', create_team, name='create_team'),
    re_path(r'^finalize_team/$', finalize_team, name='finalize_team'),
    re_path(r'^data_use_report/(?P<request_id>[^/]+)/?$', data_use_report, name='data_use_report'),
    re_path(r'^signed_agreement_form/$', signed_agreement_form, name='signed_agreement_form'),
    re_path(r'^download_dataset/$', download_dataset, name='download_dataset'),
    re_path(r'^upload_challengetasksubmission_file/$', upload_challengetasksubmission_file, name="upload_challengetasksubmission_file"),
    re_path(r'^delete_challengetasksubmission/$', delete_challengetasksubmission, name='delete_challengetasksubmission'),
    re_path(r'^update_institutional_members/$', update_institutional_members, name="update_institutional_members"),
    re_path(r'^qualtrics/$', qualtrics, name="qualtrics"),
    re_path(r'^(?P<project_key>[^/]+)/$', DataProjectView.as_view(), name="view-project"),
]
