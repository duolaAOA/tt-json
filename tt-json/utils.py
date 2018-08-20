# -*-coding:utf-8 -*-
import types
import inspect

HTTP_METHODS = ["get", "put", "post", "patch", "delete", "head", "options"]


def extract_method(wrapped_method):

    return wrapped_method.orig_func if hasattr(wrapped_method, "orig_func") else wrapped_method


def is_method(method):

    method = extract_method(method)
    return type(method) in [types.MethodType, types.FunctionType]


def is_handler_subclass(cls, classnames=("ViewHandler", "APIHandler")):
    """
    Determines if ``cls`` is indeed a subclass of ``classnames
    """
    if isinstance(cls, list):
        return any(is_handler_subclass(c) for c in cls)
    elif isinstance(cls, type):
        return any(c.__name__ in classnames for c in inspect.getmro(cls))
    else:
        raise TypeError(
            "Unexpected type `{}` for class `{}`".format(
                type(cls),
                cls
            )
        )
