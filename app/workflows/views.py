from django.views import View
from django.shortcuts import get_object_or_404

from workflows.models import WorkflowState
from workflows.models import StepState


class WorkflowStateView(View):
    """
    Generic view for rendering a workflow via its controller.
    """
    def get(self, request, workflow_state_id):
        """
        Render a workflow view.
        """
        # Get the workflow.
        workflow_state = get_object_or_404(WorkflowState, id=workflow_state_id)

        # Initialize the controller class.
        controller = workflow_state.workflow.controller(workflow_state)

        # Render it.
        return controller.get(request)


class StepStateView(View):
    """
    Generic view for rendering a step via its controller.
    """
    def get(self, request, step_state_id):
        """
        Render a step view.
        """
        # Get the step
        step_state = get_object_or_404(StepState, id=step_state_id)

        # Initialize the controller class.
        controller = step_state.step.controller(step_state)

        # Render it.
        return controller.get(request)

    def post(self, request, step_state_id):
        """
        Handle submission for a step state.
        """
        # Get the step state
        step_state = get_object_or_404(StepState, id=step_state_id)

        # Initialize the controller class.
        controller = step_state.step.controller(step_state)

        # Render it.
        return controller.post(request)

    def patch(self, request, step_state_id):
        """
        Handle submission for a step state.
        """
        # Get the step state
        step_state = get_object_or_404(StepState, id=step_state_id)

        # Initialize the controller class.
        controller = step_state.step.controller(step_state)

        # Render it.
        return controller.patch(request)
