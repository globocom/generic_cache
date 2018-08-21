# Copyright (c) 2018, Globo.com (https://github.com/globocom)
#
# License: MIT

import logging


class BaseCacheKey(object):
    '''
    This is the base class for any key used with GenericCache class.
    The keys used on GenericCache must have a timeout attribute (timeout unit is seconds)
    and a key_str to translate the Key object to a string key to be saved on the cache
    backend.

    '''

    def __init__(self, key_type, key_version="", timeout=None):
        self.key_type = key_type
        self.timeout = timeout
        self.version = key_version

    @property
    def key_str(self):
        return u"{}{}".format(self.key_type, self.version)

    def __str__(self):
        return self.key_str


def _get_func_kwargs(method, *args, **kwargs):
    '''
    Normalizes a method call args to kwargs.
    This is done to facilitated caching of different function calls with the same arg values.
    Example:
    ```
    def sum(a, b):
        return a + b
    # sum(1, 2), sum(1, b=2), sum(a=1, b=2) would all be cached with the same key
    ```

    Args:
        method (function): the method which will be called
        *args (tuple): The args (excluding self/cls) which will be called on method
        **kwargs (tuple): The kwargs which will be called on method

    Returns:
        dict: the normalized kwargs

    Example:
    >>> def instancemethod(self, a, b, c):
    ...     pass
    ... get_method_kwargs(instancemethod, (1, 2), {'c': 3})
    {'a': 1, 'b': 2, 'c': 3}
    '''
    import inspect
    from copy import copy
    from collections import OrderedDict
    
    normalized_kwargs = OrderedDict()
    args_spec = inspect.getargspec(method)
    if args_spec.varargs is not None:
        raise ValueError("method must not have vargargs on its signature")

    for i, arg in enumerate(args):
        normalized_kwargs[args_spec.args[i]] = arg
    normalized_kwargs.update(kwargs)
    return normalized_kwargs


class ArgsCacheKey(BaseCacheKey):
    '''
    Transforms args and kwargs on a key string. Useful for caching functions called
    with different values for args and/or kwargs. The timeout kwarg is reserved.
    See `key_str` docs for more information.
    '''

    def __init__(self, key_type, *args, **kwargs):
        timeout = kwargs.pop('timeout', None)
        key_version = kwargs.pop('key_version', "")
        super(ArgsCacheKey, self).__init__(
            key_type,
            timeout=timeout,
            key_version=key_version
        )
        self.args = args
        self.kwargs = kwargs
        self._key_str = None

    @property
    def key_str(self):
        '''
        str: Makes the transformation of the args and kwargs to a string.
        Example:
        >>> key = ArgsCacheKey('myfunc', 1, 2, 3, some_kw_key='test', alpha_first_key='hey')
        >>> str(key)
        'myfunc__1__2__3__alpha_first_key_hey__some_kw_key_test'

        Beware that this class is expected to be immutable, hence key_str is cached.
        So, DON'T DO THIS:
        >>> key.key_type = 'othertype'
        >>> str(key)  # Will result in
        'myfunc__1__2__3__alpha_first_key_hey__some_kw_key_test'
        Not as the expected
        'othertype__1__2__3__alpha_first_key_hey__some_kw_key_test'
        '''
        if self._key_str is None:
            base_key = str(self.key_type)
            args_str = "__".join(str(a) for a in self.args)
            kwargs_str = "__".join(
                "{k}_{v}".format(k=k, v=v) for k, v in sorted(self.kwargs.items())
            )
            self._key_str = u"{}{}".format(base_key, self.version)
            if args_str:
                self._key_str = self._key_str + "__" + args_str
            if kwargs_str:
                self._key_str = self._key_str + "__" + kwargs_str
        return self._key_str


class BaseKeyBuilder(object):
    def build_key(self, *args, **kwargs):
        raise NotImplementedError()


class FunctionKeyBuilder(BaseKeyBuilder):
    def get_normalized_kwargs(self, func, *func_args, **func_kwargs):
        return _get_func_kwargs(func, *func_args, **func_kwargs)

    def build_key(self, key_prefix, func, *func_args, **func_kwargs):
        kwargs = self.get_normalized_kwargs(func, *func_args, **func_kwargs)
        return ArgsCacheKey(key_prefix, **kwargs)


class MethodKeyBuilder(FunctionKeyBuilder):
    def get_normalized_kwargs(self, func, *func_args, **func_kwargs):
        kwargs = super(MethodKeyBuilder, self).get_normalized_kwargs(func, *func_args, **func_kwargs)
        kwargs.pop('self')
        return kwargs


class AttrsMethodKeyBuilder(MethodKeyBuilder):
    def __init__(self, attrs, *args, **kwargs):
        super(AttrsMethodKeyBuilder, self).__init__(*args, **kwargs)
        self.attrs = attrs
    
    def get_normalized_kwargs(self, func, *func_args, **func_kwargs):
        kwargs = super(AttrsMethodKeyBuilder, self).get_normalized_kwargs(func, *func_args, **func_kwargs)
        instance = func_args[0]
        for attr in self.attrs:
            kwargs[attr] = getattr(instance, attr)
        return kwargs
