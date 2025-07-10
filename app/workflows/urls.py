from django.urls import path
from django.urls import include
from rest_framework import routers

from workflows.api import WorkflowUserViewSet
from workflows.api import WorkflowViewSet
from workflows.api import StepViewSet
from workflows.api import WorkflowStateViewSet
from workflows.api import StepStateViewSet
from workflows.apps import WorkflowsConfig

app_name = WorkflowsConfig.name

router = routers.DefaultRouter()

# Workflows
router.register(r'user', WorkflowUserViewSet, basename='user')
router.register(r'workflow', WorkflowViewSet, basename='workflow')
router.register(r'workflow-state', WorkflowStateViewSet, basename='workflow-state')
router.register(r'admin/workflow-state', WorkflowStateViewSet, basename='admin-workflow-state')
router.register(r'step', StepViewSet, basename='step')
router.register(r'step-state', StepStateViewSet, basename='step-state')
router.register(r'admin/step-state', StepStateViewSet, basename='admin-step-state')


urlpatterns = [
    path('api/v1/', include((router.urls, "workflows-api-v1"), namespace="v1")),
]
