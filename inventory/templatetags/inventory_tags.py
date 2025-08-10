from django import template

register = template.Library()

@register.filter
def attr(obj, arg):
    """
    Gets an attribute of an object dynamically.
    Useful for accessing form field attributes in templates.
    Example: {{ form|attr:"some_attribute" }}
    """
    return getattr(obj, arg, '')

@register.filter
def capitalize(value):
    """
    Custom filter to capitalize the first letter of a string.
    Equivalent to Python's str.capitalize().
    """
    if isinstance(value, str):
        return value.capitalize()
    return value