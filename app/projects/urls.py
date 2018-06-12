from django.conf.urls import url

from .views import list_data_projects
from .views import list_data_challenges
from .views import request_access
from .views import submit_user_permission_request
from .views_manage import manage_contest
from .views_manage import manage_project
from .views_manage import manage_project_team
from .views import signed_agreement_form
from .views import save_signed_agreement_form
from .views import save_dynamic_signed_agreement_form
from .views import signout
from .views_manage import manage_team
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
from .views_files import upload_participantsubmission_file
from .views_files import download_team_submissions
from .views_files import delete_participantsubmission

urlpatterns = (
    url(r'^$', list_data_projects),
    url(r'^list_data_projects/$', list_data_projects),
    url(r'^list_data_challenges/$', list_data_challenges),
    url(r'^request_access/$', request_access),
    url(r'^submit_user_permission_request/$', submit_user_permission_request),
    url(r'^manage/(?P<project_key>[^/]+)/$', manage_contest, name='manage_contest'),
    url(r'^manage/(?P<project_key>[^/]+)/(?P<team_leader>[^/]+)/$', manage_team),
    url(r'^manage_project/(?P<project_key>[^/]+)/$', manage_project, name='manage_project'),
    url(r'^manage_project/(?P<project_key>[^/]+)/(?P<team_leader>[^/]+)/$', manage_project_team),
    url(r'^save_signed_agreement_form', save_signed_agreement_form),
    url(r'^save_dynamic_signed_agreement_form', save_dynamic_signed_agreement_form),
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
    url(r'^upload_participantsubmission_file/$', upload_participantsubmission_file),
    url(r'^download_team_submissions/$', download_team_submissions),
    url(r'^delete_participantsubmission/$', delete_participantsubmission),
    url(r'^(?P<project_key>[^/]+)/$', DataProjectView.as_view()),
)
