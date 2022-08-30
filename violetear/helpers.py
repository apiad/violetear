from functools import wraps
from inspect import isgenerator


def style_method(function):
    @wraps(function)
    def wrapper(self, *args, **kwargs):
        function(self, *args, **kwargs)
        return self

    return wrapper


def flatten(items):
    for item in items:
        if isinstance(item, (list, tuple)) or isgenerator(item):
            yield from flatten(item)
        else:
            yield item
