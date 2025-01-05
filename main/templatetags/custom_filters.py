from django import template

register = template.Library()

@register.filter
def dict_key(value, arg):
    return value.get(arg)
