from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def keyvalue(passed_dictionary, key):
    return passed_dictionary[key]

@register.filter
def keyvalue_permission_scheme(passed_dictionary, key):
    return passed_dictionary[key]['permission_scheme']

@register.filter
def permission_requested(dictionary, project_key):
    return project_key in dictionary

@register.filter
def is_request_granted(dictionary, project_key):
    return dictionary[project_key]['request_granted']

@register.filter
def get_date_requested(dictionary, project_key):
    return dictionary[project_key]["date_requested"]

@register.simple_tag
def modal_contact_form_button(text='Contact us', classes='btn btn-primary btn-md'):

    return mark_safe("""
        <button class='contact-form-button {}'>{}</button>
    """.format(classes, text))


@register.simple_tag
def modal_contact_form_link(text='Contact us', classes=''):

    return mark_safe("""
        <a href=# class='contact-form-button {}'>{}</a>
    """.format(classes, text))

