import re
from django import template

register = template.Library()

@register.filter
def dict_key(value, arg):
    return value.get(arg)

@register.filter(name='markdown_bold')
def markdown_bold(text):
    """Converts markdown bold syntax to HTML bold tags."""
    return re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
