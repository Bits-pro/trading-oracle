from django import template

register = template.Library()


@register.filter
def get_item(mapping, key):
    if mapping is None:
        return None
    return mapping.get(key)


@register.filter
def format_number(value, decimals=2):
    if value is None:
        return ''
    try:
        decimals = int(decimals)
    except (TypeError, ValueError):
        decimals = 2
    try:
        number = float(value)
    except (TypeError, ValueError):
        return value
    formatted = f"{number:,.{decimals}f}"
    return formatted.replace(",", " ")
