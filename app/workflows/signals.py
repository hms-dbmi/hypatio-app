from django.db.models.signals import post_delete, pre_delete
from django.dispatch import receiver

from workflows.models import WorkflowState
from workflows.models import StepState
from workflows.models import StepStateReview
from workflows.models import StepStateInitialization

deleting_workflow_states = set()

@receiver(pre_delete, sender=WorkflowState)
def workflow_state_pre_delete(sender, instance, **kwargs):
    deleting_workflow_states.add(instance.id)

@receiver(post_delete, sender=WorkflowState)
def workflow_state_pre_delete(sender, instance, **kwargs):
    deleting_workflow_states.remove(instance.id)

@receiver(post_delete, sender=StepState)
def step_state_post_delete(sender, instance, using, **kwargs):

    # Ensure the workflow state object exists
    if deleting_workflow_states and instance.workflow_state.id in deleting_workflow_states:
        return

    # Re-create the step state
    instance.workflow_state.set_step_states()

    # Update the workflow steps
    instance.workflow_state.set_step_statuses()


@receiver(post_delete, sender=StepStateReview)
def step_state_review_post_delete(sender, instance, using, **kwargs):
    # Update the workflow steps
    instance.step_state.workflow_state.set_step_statuses()


@receiver(post_delete, sender=StepStateInitialization)
def step_state_initialization_post_delete(sender, instance, using, **kwargs):
    # Update the workflow steps
    instance.step_state.workflow_state.set_step_statuses()
