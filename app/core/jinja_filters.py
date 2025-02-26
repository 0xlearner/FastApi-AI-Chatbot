import json

from jinja2 import pass_context


def fromjson(value):
    """Convert JSON string to Python object with error handling"""
    try:
        if isinstance(value, str):
            return json.loads(value)
        elif isinstance(value, list):
            return value
        return []
    except (TypeError, json.JSONDecodeError):
        return []


@pass_context
def dict_item(context, dict_obj, key, default=None):
    """Safe dictionary access for Jinja2 templates"""
    if not dict_obj:
        return default
    return dict_obj.get(str(key), default)
