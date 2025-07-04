from django.http import HttpResponse, HttpResponseForbidden
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
        controller = workflow_state.workflow.get_controller(workflow_state)

        # Render it.
        return controller.get(request)

    def post(self, request, workflow_state_id):
        """
        Handle input from a workflow view.
        """
        # Get the workflow.
        workflow_state = get_object_or_404(WorkflowState, id=workflow_state_id)

        # Initialize the controller class.
        controller = workflow_state.workflow.get_controller(workflow_state)

        # Render it.
        return controller.post(request)


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
        controller = step_state.step.get_controller(step_state)

        # Render it.
        return controller.get(request)

    def post(self, request, step_state_id):
        """
        Handle submission for a step state.
        """
        # Get the step state
        step_state = get_object_or_404(StepState, id=step_state_id)

        # Initialize the controller class.
        controller = step_state.step.get_controller(step_state)

        # Render it.
        return controller.post(request)

    def patch(self, request, step_state_id):
        """
        Handle submission for a step state.
        """
        # Get the step state
        step_state = get_object_or_404(StepState, id=step_state_id)

        # Initialize the controller class.
        controller = step_state.step.get_controller(step_state)

        # Render it.
        return controller.patch(request)


class WorkflowStateAdminView(View):
    """
    Generic admin view for rendering a workflow via its controller.
    """
    def check_permissions(self, request):
        """
        Check if the user has permission to access this view.
        """
        # Only allow staff users to access this view.
        return request.user.is_staff

    def dispatch(self, request, *args, **kwargs):

        # Check if the user is an admin or not.
        if not self.check_permissions(request):

            # If not, return a 403 Forbidden response.
            return HttpResponseForbidden("You do not have permission to access this resource.")

        return super().dispatch(request, *args, **kwargs)

    def get(self, request, workflow_state_id):
        """
        Render a workflow view.
        """
        # Get the workflow.
        workflow_state = get_object_or_404(WorkflowState, id=workflow_state_id)

        # Initialize the controller class.
        controller = workflow_state.workflow.get_controller(workflow_state, admin=True)

        # Render it.
        return controller.admin_get(request)

    def post(self, request, workflow_state_id):
        """
        Handle input from a workflow view.
        """
        # Get the workflow.
        workflow_state = get_object_or_404(WorkflowState, id=workflow_state_id)

        # Initialize the controller class.
        controller = workflow_state.workflow.get_controller(workflow_state, admin=True)

        # Render it.
        return controller.admin_post(request)

    def patch(self, request, workflow_state_id):
        """
        Handle input from a workflow view.
        """
        # Get the workflow.
        workflow_state = get_object_or_404(WorkflowState, id=workflow_state_id)

        # Initialize the controller class.
        controller = workflow_state.workflow.get_controller(workflow_state, admin=True)

        # Render it.
        return controller.admin_patch(request)


class StepStateAdminView(View):
    """
    Generic admin view for rendering a step via its controller.
    """
    def check_permissions(self, request):
        """
        Check if the user has permission to access this view.
        """
        # Only allow staff users to access this view.
        return request.user.is_staff

    def dispatch(self, request, *args, **kwargs):

        # Check if the user is an admin or not.
        if not self.check_permissions(request):

            # If not, return a 403 Forbidden response.
            return HttpResponseForbidden("You do not have permission to access this resource.")

        return super().dispatch(request, *args, **kwargs)

    def get(self, request, step_state_id):
        """
        Render a step view.
        """
        # Get the step
        step_state = get_object_or_404(StepState, id=step_state_id)

        # Initialize the controller class.
        controller = step_state.step.get_controller(step_state, admin=True)

        # Check if implemented
        if not hasattr(controller, 'admin_get'):
            return HttpResponse("Admin view not implemented for this method.", status=405)

        # Render it.
        return controller.admin_get(request)

    def post(self, request, step_state_id):
        """
        Handle submission for a step state.
        """
        # Get the step state
        step_state = get_object_or_404(StepState, id=step_state_id)

        # Initialize the controller class.
        controller = step_state.step.get_controller(step_state, admin=True)

        # Check if implemented
        if not hasattr(controller, 'admin_post'):
            return HttpResponse("Admin view not implemented for this method.", status=405)

        # Render it.
        return controller.admin_post(request)

    def patch(self, request, step_state_id):
        """
        Handle submission for a step state.
        """
        # Get the step state
        step_state = get_object_or_404(StepState, id=step_state_id)

        # Initialize the controller class.
        controller = step_state.step.get_controller(step_state, admin=True)

        # Check if implemented
        if not hasattr(controller, 'admin_patch'):
            return HttpResponse("Admin view not implemented for this method.", status=405)

        # Render it.
        return controller.admin_patch(request)


class StepStateInitializationView(View):
    """
    Generic admin view for rendering a step's initialization via its controller.
    """
    def check_permissions(self, request):
        """
        Check if the user has permission to access this view.
        """
        # Only allow staff users to access this view.
        return request.user.is_staff

    def dispatch(self, request, *args, **kwargs):

        # Check if the user is an admin or not.
        if not self.check_permissions(request):

            # If not, return a 403 Forbidden response.
            return HttpResponseForbidden("You do not have permission to access this resource.")

        return super().dispatch(request, *args, **kwargs)

    def get(self, request, step_state_id):
        """
        Render a step view.
        """
        # Get the step
        step_state = get_object_or_404(StepState, id=step_state_id)

        # Initialize the controller class.
        controller = step_state.get_initialization_controller()

        # Check if implemented
        if not hasattr(controller, 'get'):
            return HttpResponse("Admin view not implemented for this method.", status=405)

        # Render it.
        return controller.get(request)

    def post(self, request, step_state_id):
        """
        Handle submission for a step state.
        """
        # Get the step state
        step_state = get_object_or_404(StepState, id=step_state_id)

        # Initialize the controller class.
        controller = step_state.get_initialization_controller()

        # Check if implemented
        if not hasattr(controller, 'post'):
            return HttpResponse("Admin view not implemented for this method.", status=405)

        # Render it.
        return controller.post(request)

    def patch(self, request, step_state_id):
        """
        Handle submission for a step state.
        """
        # Get the step state
        step_state = get_object_or_404(StepState, id=step_state_id)

        # Initialize the controller class.
        controller = step_state.get_initialization_controller()

        # Check if implemented
        if not hasattr(controller, 'patch'):
            return HttpResponse("Admin view not implemented for this method.", status=405)

        # Render it.
        return controller.patch(request)


class StepStateReviewView(View):
    """
    Generic admin view for rendering a step's review via its controller.
    """
    def check_permissions(self, request):
        """
        Check if the user has permission to access this view.
        """
        # Only allow staff users to access this view.
        return request.user.is_staff

    def dispatch(self, request, *args, **kwargs):

        # Check if the user is an admin or not.
        if not self.check_permissions(request):

            # If not, return a 403 Forbidden response.
            return HttpResponseForbidden("You do not have permission to access this resource.")

        return super().dispatch(request, *args, **kwargs)

    def get(self, request, step_state_id):
        """
        Render a step view.
        """
        # Get the step
        step_state = get_object_or_404(StepState, id=step_state_id)

        # Initialize the controller class.
        controller = step_state.get_review_controller()

        # Check if implemented
        if not hasattr(controller, 'get'):
            return HttpResponse("Admin view not implemented for this method.", status=405)

        # Render it.
        return controller.get(request)

    def post(self, request, step_state_id):
        """
        Handle submission for a step state.
        """
        # Get the step state
        step_state = get_object_or_404(StepState, id=step_state_id)

        # Initialize the controller class.
        controller = step_state.get_review_controller()

        # Check if implemented
        if not hasattr(controller, 'post'):
            return HttpResponse("Admin view not implemented for this method.", status=405)

        # Render it.
        return controller.post(request)

    def patch(self, request, step_state_id):
        """
        Handle submission for a step state.
        """
        # Get the step state
        step_state = get_object_or_404(StepState, id=step_state_id)

        # Initialize the controller class.
        controller = step_state.get_review_controller()

        # Check if implemented
        if not hasattr(controller, 'patch'):
            return HttpResponse("Admin view not implemented for this method.", status=405)

        # Render it.
        return controller.patch(request)
