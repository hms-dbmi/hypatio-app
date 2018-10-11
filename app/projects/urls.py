from django.conf.urls import url

from .views import list_data_projects
from .views import submit_user_permission_request
from .views import signed_agreement_form
from .views import save_signed_agreement_form
from .views import save_dynamic_signed_agreement_form
from .views import save_signed_external_agreement_form
from .views import signout
from .views import DataProjectView

from .views_teams import join_team
from .views_teams import leave_team
from .views_teams import create_team
from .views_teams import approve_team_join
from .views_teams import reject_team_join
from .views_teams import finalize_team
from .views_teams import change_team_status
from .views_teams import delete_team
from .views_teams import save_team_comment
from .views_teams import change_signed_form_status
from .views_teams import download_signed_form

from .views_files import download_dataset
from .views_files import upload_challengetasksubmission_file
from .views_files import download_team_submissions
from .views_files import delete_challengetasksubmission

urlpatterns = (
    url(r'^$', list_data_projects),
    url(r'^submit_user_permission_request/$', submit_user_permission_request),
    url(r'^save_signed_agreement_form', save_signed_agreement_form),
    url(r'^save_dynamic_signed_agreement_form', save_dynamic_signed_agreement_form),
    url(r'^save_signed_external_agreement_form', save_signed_external_agreement_form),
    url(r'^signout/$', signout),
    url(r'^join_team/$', join_team),
    url(r'^leave_team/$', leave_team),
    url(r'^approve_team_join/$', approve_team_join),
    url(r'^reject_team_join/$', reject_team_join),
    url(r'^create_team/$', create_team),
    url(r'^finalize_team/$', finalize_team),
    url(r'^change_team_status/$', change_team_status),
    url(r'^delete_team/$', delete_team),
    url(r'^save_team_comment/$', save_team_comment),
    url(r'^change_signed_form_status/$', change_signed_form_status),
    url(r'^download_signed_form/$', download_signed_form),
    url(r'^signed_agreement_form/$', signed_agreement_form),
    url(r'^download_dataset/$', download_dataset),
    url(r'^upload_challengetasksubmission_file/$', upload_challengetasksubmission_file),
    url(r'^download_team_submissions/$', download_team_submissions),
    url(r'^delete_challengetasksubmission/$', delete_challengetasksubmission),
    url(r'^(?P<project_key>[^/]+)/$', DataProjectView.as_view()),
)
