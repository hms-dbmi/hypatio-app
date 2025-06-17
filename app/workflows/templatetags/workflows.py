from django import template
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def workflow(workflow_state):
    """Renders the given workflow container."""
    # Set context
    context = {
        "workflow": workflow_state,
    }
    
    # Load the template
    html = render_to_string("workflows/workflow-container.html", context=context)
    
    return mark_safe(html)