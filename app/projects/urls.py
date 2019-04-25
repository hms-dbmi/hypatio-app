from django.conf.urls import url

from projects.views import list_data_projects
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

app_name = 'projects'
urlpatterns = [
    url(r'^$', list_data_projects, name='index'),
    url(r'^submit_user_permission_request/$', submit_user_permission_request, name='submit_user_permission_request'),
    url(r'^save_signed_agreement_form', save_signed_agreement_form, name='save_signed_agreement_form'),
    url(r'^save_signed_external_agreement_form', save_signed_external_agreement_form, name='save_signed_external_agreement_form'),
    url(r'^join_team/$', join_team, name='join_team'),
    url(r'^leave_team/$', leave_team, name='leave_team'),
    url(r'^approve_team_join/$', approve_team_join, name='approve_team_join'),
    url(r'^reject_team_join/$', reject_team_join, name='reject_team_join'),
    url(r'^create_team/$', create_team, name='create_team'),
    url(r'^finalize_team/$', finalize_team, name='finalize_team'),
    url(r'^signed_agreement_form/$', signed_agreement_form, name='signed_agreement_form'),
    url(r'^download_dataset/$', download_dataset, name='download_dataset'),
    url(r'^upload_challengetasksubmission_file/$', upload_challengetasksubmission_file, name="upload_challengetasksubmission_file"),
    url(r'^delete_challengetasksubmission/$', delete_challengetasksubmission, name='delete_challengetasksubmission'),
    url(r'^(?P<project_key>[^/]+)/$', DataProjectView.as_view(), name="view-project"),
]
