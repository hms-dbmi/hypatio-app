from django.urls import path
from django.urls import include
from rest_framework import routers

from workflows.api import WorkflowUserViewSet
from workflows.api import WorkflowViewSet
from workflows.api import StepViewSet
from workflows.api import WorkflowStateViewSet
from workflows.api import StepStateViewSet
from workflows.apps import WorkflowsConfig
from workflows.views import WorkflowStateView
from workflows.views import StepStateView
from workflows.views import WorkflowStateAdminView
from workflows.views import StepStateAdminView

app_name = WorkflowsConfig.name

router = routers.DefaultRouter()

# Workflows
router.register(r'user', WorkflowUserViewSet, basename='user')
router.register(r'workflow', WorkflowViewSet, basename='workflow')
router.register(r'workflow-state', WorkflowStateViewSet, basename='workflow-state')
router.register(r'step', StepViewSet, basename='step')
router.register(r'step-state', StepStateViewSet, basename='step-state')


urlpatterns = [
    path('state/workflow/<uuid:workflow_state_id>', WorkflowStateView.as_view(), name='workflow-state'),
    path('state/step/<uuid:step_state_id>', StepStateView.as_view(), name='step-state'),
    path('admin/state/workflow/<uuid:workflow_state_id>', WorkflowStateAdminView.as_view(), name='workflow-state-admin'),
    path('admin/state/step/<uuid:step_state_id>', StepStateAdminView.as_view(), name='step-state-admin'),
    path('api/v1/', include((router.urls, "workflows-api-v1"), namespace="v1")),
]
