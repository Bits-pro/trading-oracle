"""
Custom template filters for the dashboard
"""
from django import template

register = template.Library()


@register.filter(name='replace_underscore')
def replace_underscore(value):
    """Replace underscores with spaces"""
    if value:
        return str(value).replace('_', ' ')
    return value


@register.filter(name='format_percentage')
def format_percentage(value):
    """Format a decimal as percentage"""
    try:
        return f"{float(value):.2f}%"
    except (ValueError, TypeError):
        return value


@register.filter(name='abs_value')
def abs_value(value):
    """Return absolute value"""
    try:
        return abs(float(value))
    except (ValueError, TypeError):
        return value


@register.filter(name='format_roi')
def format_roi(value):
    """Format ROI with + or - sign"""
    try:
        val = float(value)
        if val > 0:
            return f"+{val:.2f}%"
        else:
            return f"{val:.2f}%"
    except (ValueError, TypeError):
        return value
