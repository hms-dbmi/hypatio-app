import json

from django import template
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

from workflows.models import StepState

register = template.Library()

@register.simple_tag(takes_context=True)
def step_is_expanded(context, step):
    """Return True if the step state should be rendered expanded or not."""
    # Don't automatically expand indefinite steps in administration views.
    if context.get("is_administration") and step.status == StepState.Status.Indefinite.value:
        return False

    return step.status in [
        StepState.Status.Uninitialized.value,
        StepState.Status.Current.value,
        StepState.Status.Unreviewed.value,
        StepState.Status.Indefinite.value,
    ]

@register.filter
def workflows(workflow_states, admin=False):
    """Renders the given workflows container."""

    # Set context
    context = {
        "workflows": workflow_states,
        "admin": admin,
    }

    # Load the template
    html = render_to_string("workflows/workflows-container.html", context=context)

    return mark_safe(html)

@register.filter
def workflow(workflow_state, admin=False):
    """Renders the given workflow container."""

    # Set context
    context = {
        "workflow": workflow_state,
        "admin": admin,
    }

    # Load the template
    html = render_to_string("workflows/workflow-container.html", context=context)

    return mark_safe(html)


@register.filter
def workflow_admin(workflow_state):
    """Renders the given workflow container for an administrator."""

    # Set context
    context = {
        "workflow": workflow_state,
        "admin": True,
    }

    # Load the template
    html = render_to_string("workflows/workflow-container.html", context=context)

    return mark_safe(html)

@register.filter
def pretty_json(value):
    return json.dumps(value, indent=4)
