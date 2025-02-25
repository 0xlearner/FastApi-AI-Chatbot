import json


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
