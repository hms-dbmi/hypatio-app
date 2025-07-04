from workflows.controllers import BaseController
from workflows.controllers import get_controller_choices

import logging
logger = logging.getLogger(__name__)


def get_step_initialization_controller_choices() -> list[(str, str)]:
    """
    Returns a list of tuples containing a class's fully-qualified name and its short name for step initialization controllers.
    """
    return get_controller_choices(BaseStepInitializationController)


class BaseStepInitializationController(BaseController):
    """
    Controller for initializing the step state.
    """
    @classmethod
    def name(cls):
        """
        Returns the name of the controller.
        """
        return "Base Step Initialization Controller"


class RexplainVideoStepStateInitializationController(BaseStepInitializationController):
    """
    Controller for initializing the Rexplain video step state.
    """
    template = "workflows/initializations/rexplain-video.html"
    
    @classmethod
    def name(cls):
        """
        Returns the name of the controller.
        """
        return "ReXplain Video Step State Initialization Controller"

    def __init__(self):
        super().__init__()
        # Additional initialization logic for Rexplain video step state can be added here

    def get(self, request, *args, **kwargs):
        """
        Build the context for rendering the step.
        """
        logger.debug(f"[{self.__class__.__name__}][get]")

    def post(self, request, *args, **kwargs):
        """
        Build the context for rendering the step.
        """
        logger.debug(f"[{self.__class__.__name__}][post]")