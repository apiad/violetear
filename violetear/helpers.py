from functools import wraps


def style_method(function):
    @wraps(function)
    def wrapper(self, *args, **kwargs):
        function(self, *args, **kwargs)
        return self

    return wrapper
