from django import template

register = template.Library()

@register.filter
def get_item(list_, index):
    try:
        return list_[int(index)]
    except (IndexError, ValueError, TypeError):
        return None
