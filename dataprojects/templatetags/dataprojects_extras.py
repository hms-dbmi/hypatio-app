from django import template

register = template.Library()


@register.filter
def keyvalue(passed_dictionary, key):
    return passed_dictionary[key]

