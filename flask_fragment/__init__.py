# -*- coding: utf-8 -*-
"""
    flask.ext.fragment
    ------------------

    Flask extension to implement fragment caching.

    :copyright: (c) 2013 by Alexey Poryadin.
    :license: MIT, see LICENSE for more details.
"""
import flask
import jinja2
import inspect
from functools import partial
from flask import Flask, Blueprint
from flask import _app_ctx_stack as stack


class Fragment(object):

    def __init__(self, app=None):
        self.mod = None
        self.endpoint = None
        self.resethandler = None
        self.app = app
        if app is not None:
            self.init_app(app)

    def __call__(self, mod, endpoint=None, resethandler=None):
        """Decorator to define function as fragment cached view

        Args:
            mod: Flask app or blueprint
            endpoint: Access point
        """
        self.mod = mod
        self.endpoint = endpoint
        self.resethandler = resethandler

        def decorator(fragment_view):
            fragment_view_name = fragment_view.__name__
            fragment_view.cache_endpoint = self.endpoint if self.endpoint else fragment_view_name
            fragment_view.cache_resethandler = resethandler
            if self.endpoint:
                rule = '/{0}'.format(self.endpoint)
            elif isinstance(mod, Blueprint):
                rule = '/{0}.{1}'.format(mod.name, fragment_view_name)
            else:
                rule = '/{0}'.format(fragment_view_name)
            fragment_view_signature = inspect.signature(fragment_view)
            fragment_view.args_names = fragment_view_signature.parameters
            for arg_name in fragment_view.args_names:
                rule += '/<{0}>'.format(arg_name)
            mod.add_url_rule(rule, fragment_view_name, fragment_view)
            return fragment_view
        return decorator

    def init_app(self, app):
        self.app = app
        self.app.context_processor(lambda: {'fragment': self._fragment_tmpl_func})
    
    def resethandler(self, fragment_view):
        """Decorator sets reset fragment cache handler for `fragment_view` function."""
        def decorator(handler):
            fragment_view.cache_resethandler = handler
            return handler
        return decorator        

    def reset(self, target, *args, **kwargs):
        """Resets cache for fragment cached view
        
        Args:
            target: Endpoint or the view itself.
        """
        if isinstance(target, str):
            fragment_view = flask.current_app.view_functions.get(target)
            if fragment_view is None:
                raise ValueError('Not found view for endpoint "{0}"'.format(target))
        else:
            fragment_view = target
        if fragment_view.cache_resethandler is None:
            # Tries default resethandler handler
            try:
                for N in range(0, len(args)):
                    kwargs[fragment_view.args_names[N]] = args[N]
                url = flask.url_for(fragment_view.cache_endpoint, **kwargs)
            except Exception as exc:
                raise RuntimeError('Cannot reset cache for "{0}",'
                    ' resethandler is not set and default handler canot'
                    ' build URL. Detail: "{1}"'.format(fragment_view, exc))
            self.reset_url(url)
        else:
            fragment_view.cache_resethandler(*args, **kwargs)
        
    
    def reset_url(self, url):
        """Resets cache for URL
        
        Args:
            url: URL value
        """
        raise NotImplementedError('Need to look around ngx_cache_purge')

    def _fragment_tmpl_func(self, endpoint, *args, **kwargs):
        """Template context function that renders fragment cached view.
        
        Accepts `*args`, `**kwargs` that must match by the number and by the
        order of parameters from  function that defined with 'endpoint'.
        
        Args:
            endpoint: The endpoint name.
        """
        func = flask.current_app.view_functions.get(endpoint)
        if func is not None:
            for N in range(0, len(args)):
                kwargs[func.args_names[N]] = args[N]
            url = flask.url_for(endpoint, **kwargs)
            return self._render(url, partial(func, **kwargs))
        raise ValueError('Not found view for endpoint "{0}"'.format(endpoint))

    def _render(self, url, deferred_view):
        if self.app.config.get('FRAGMENT_SSI', False):
            content = '<!--# include virtual="{0}" -->'.format(url)
        else:
            response = deferred_view()
            content = response.get_data().decode(response.mimetype_params['charset'])
        return jinja2.Markup(content)
