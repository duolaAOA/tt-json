# -*-coding:utf-8 -*-

import inspect
import pkgutil
import importlib
from itertools import chain
from functools import reduce

from .utils import is_method, extract_method, is_handler_subclass
from .utils import HTTP_METHODS


def get_routes(package):

    return list(chain(*[get_module_routes(mod_name) for mod_name in
                        gen_submodule_names(package)]))


def gen_submodule_names(package):
    """
    Walk package and yield names of all submodules
    :param package:   The package to get submodule names of
    :return:   Iterator that yields names of all submodules of ``package``
    """
    for importer, mod_name, ispkg in pkgutil.walk_packages(
        path=package.__path__,
        prefix=package.__name__ + '.',
        onerror=lambda x: None
    ):

        yield mod_name


def get_module_routes(module_name, custom_routes=None, exclusions=None,
                      arg_pattern=r'?P<{}>[a-zA-Z0-9_\-]+)'):
    """

    :param module_name:  str   Name of the module to get routes
    :param custom_routes:   [(str, RequestHandler), ... ]    List of routes
    :param exclusions:  [str, str, ...]   List of RequestHandler names that routes should not be
        generated for
    :param arg_pattern:  str   extra arguments of any method
    :return:   list of routes
    """
    def has_method(module, cls_name, method_name):

        return all([method_name in vars(getattr(module, cls_name)),
                   is_method(reduce(getattr, [module_name, cls_name, method_name]))
                   ])

    def yield_args(module, cls_name, method_name):
        """
        :return:   list   List of arg names from method_name except ``self``
        """
        wrapped_method = reduce(getattr, [module, cls_name, method_name])
        method = extract_method(wrapped_method)
        argspec_args = getattr(method, "__argspec_args", inspect.getfullargspec(method).args)

        return [a for a in argspec_args if a not in ["self"]]

    def generate_auto_route(module, module_name, cls_name, method_name, url_name):
        """
        url for auto_route
        :return    Constructed URL based on given arguments
        """
        def get_handler_name():
            """
            Get handler identifier for URL
            """
            if url_name == "__self__":
                if cls_name.lower().endswith("handler"):
                    return cls_name.lower().replace("handler", '', 1)
                return cls_name.lower()
            else:
                return url_name

        def get_arg_route():
            """
            Get remainder of URL determined by method argspec
            """
            if yield_args(module, cls_name, method_name):
                return "/{}/?$".format("/".join(
                    [arg_pattern.format(arg_name) for arg_name in
                     yield_args(module, cls_name, method_name)]
                ))
            return r"/?"

        return "/{}/{}{}".format(
            "/".join(module_name.split(".")[1:]), get_handler_name(), get_arg_route()
        )

    if not custom_routes:
        custom_routes = []
    if not exclusions:
        exclusions = []

    # Import module so we can get its request handlers
    module = importlib.import_module(module_name)

    # Generate list of RequestHandler names in custom_routes
    custom_routes_s = [c.__name__ for r , c in custom_routes]

    rhs = {cls_name: cls for (cls_name, cls) in inspect.getmembers(module, inspect.isclass)}

    # Generate a route for each "name" specified in the
    #   __url_names__ attribute of the handler
    auto_routes = list(chain(*[
        list(set(chain(*[
            [
                (
                    generate_auto_route(
                        module, module_name, cls_name, method_name, url_name
                    ),
                    getattr(module, cls_name)
                ) for url_name in getattr(module, cls_name).__url_names__
            ] + [
                (
                    url,
                    getattr(module, cls_name)
                ) for url in getattr(module, cls_name).__urls__
            ]
            for method_name in HTTP_METHODS if has_method(
                module, cls_name, method_name
            )
        ])))
        for cls_name, cls in rhs.items()
        if is_handler_subclass(cls) and cls_name not in (custom_routes_s + exclusions)
    ]))

    routes = auto_routes + custom_routes
    return routes
