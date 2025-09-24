from django.db.models.signals import post_delete, pre_delete
from django.dispatch import receiver

from workflows.models import WorkflowState
from workflows.models import StepState
from workflows.models import StepStateReview
from workflows.models import StepStateInitialization


@receiver(post_delete, sender=StepState)
def step_state_post_delete(sender, instance, using, **kwargs):

    # Do not do this if we are deleting the WorkflowState
    if kwargs.get("origin") and kwargs["origin"].model is WorkflowState:
        return

    # Re-create the step state
    instance.workflow_state.set_step_states()

    # Update the workflow steps
    instance.workflow_state.set_step_statuses()


@receiver(post_delete, sender=StepStateReview)
def step_state_review_post_delete(sender, instance, using, **kwargs):

    # Do not do this if we are deleting the WorkflowState
    if kwargs.get("origin") and kwargs["origin"].model is WorkflowState:
        return

    try:
        # Update the workflow steps
        instance.step_state.workflow_state.set_step_statuses()
    except StepState.DoesNotExist:
        pass


@receiver(post_delete, sender=StepStateInitialization)
def step_state_initialization_post_delete(sender, instance, using, **kwargs):

    # Do not do this if we are deleting the WorkflowState
    if kwargs.get("origin") and kwargs["origin"].model is WorkflowState:
        return

    # Update the workflow steps
    instance.step_state.workflow_state.set_step_statuses()
