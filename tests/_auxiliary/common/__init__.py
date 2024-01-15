#!/usr/bin/env python3
# -*- coding: utf-8 -*-

assert "__main__" != __name__


def _private():
    from . import module_helpers as _module_helpers_module
    from . import property_collector as _property_collector_module

    _make_lazy = _module_helpers_module.lazy_attributes.make_getter
    _make_property_collector = _property_collector_module.make

    return _make_property_collector(lazy = _make_lazy(dictionary = dict(
        PropertyCollector = lambda module: module.property_collector.Class
    )))


_private = _private()

__all__ = _private.lazy.keys
__date__ = None
__author__ = None
__version__ = None
__credits__ = None
_fields = tuple()
__bases__ = tuple()


def __getattr__(name: str): return _private.lazy(name = name)
