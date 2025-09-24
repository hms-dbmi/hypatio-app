from workflows.models import WorkflowState
from workflows.controllers import BaseController
from workflows.controllers import get_controller_choices

import logging
logger = logging.getLogger(__name__)


def get_workflow_controller_choices() -> list[(str, str)]:
    """
    Returns a list of tuples containing a class's fully-qualified name and its short name for workflow controllers.
    """
    return get_controller_choices(BaseWorkflowController)


class BaseWorkflowController(BaseController):
    """
    Controller for a workflow.
    """
    def __init__(self, workflow_state, is_administration=False):
        self.workflow_state = workflow_state
        self.is_administration = is_administration

    @classmethod
    def name(cls):
        """
        Returns the name of the controller.
        """
        return "Base Workflow Controller"

    def template(self, request) -> str:
        """
        Returns the name of the template to be used for rendering the WorkflowState object.
        """
        return "workflows/workflow.html" if not self.is_administration else "workflows/admin/workflow.html"

    def render_context(self, request) -> dict:
        """
        Returns the context to be used for rendering the WorkflowState object.
        """
        # Retrieve step states
        step_states = self.workflow_state.get_ordered_step_states()

        return {
            "WorkflowStateStatus": WorkflowState.Status.__members__,
            "workflow": self.workflow_state,
            "steps": step_states,
            "admin": self.is_administration,
        }
