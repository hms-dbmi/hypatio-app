from django.conf.urls import url

from manage.views import DataProjectManageView

urlpatterns = (
    # url(r'^$', LIST_PROJECTS_YOU_MANAGE),
    url(r'^(?P<project_key>[^/]+)/$', DataProjectManageView.as_view()),
)
