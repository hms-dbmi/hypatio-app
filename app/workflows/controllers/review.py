from workflows.controllers import BaseController
from workflows.controllers import get_controller_choices


def get_step_review_controller_choices() -> list[(str, str)]:
    """
    Returns a list of tuples containing a class's fully-qualified name and its short name for step review controllers.
    """
    return get_controller_choices(BaseStepReviewController)


class BaseStepReviewController(BaseController):
    """
    Controller for managing reviews for states of this step.
    """

    @classmethod
    def name(cls):
        """
        Returns the name of the controller.
        """
        return "Base Step Review Controller"


class RexplainFileUploadReviewController(BaseStepReviewController):
    """
    Controller for managing reviews for states of this step.
    """

    @classmethod
    def name(cls):
        """
        Returns the name of the controller.
        """
        return "Rexplain File Upload Review Controller"
