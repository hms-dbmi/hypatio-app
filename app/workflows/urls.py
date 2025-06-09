from django.urls import path, re_path

from workflows.apps import WorkflowsConfig
from workflows.views import WorkflowStateView
from workflows.views import StepStateView

app_name = WorkflowsConfig.name

urlpatterns = [
    path('state/workflow/<uuid:workflow_state_id>', WorkflowStateView.as_view(), name='workflow-state'),
    path('state/step/<uuid:step_state_id>', StepStateView.as_view(), name='step-state'),
]
