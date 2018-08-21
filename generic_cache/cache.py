# Copyright (c) 2018, Globo.com (https://github.com/globocom)
#
# License: MIT

import logging
from .backend import BaseBackend

__all__ = [
    'BaseCacheKey', 'ArgsCacheKey', 'GenericCache',
]


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


def _get_method_kwargs(method, *args, **kwargs):
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
    kwargs = copy(kwargs)
    args_spec = inspect.getargspec(method)
    if args_spec.varargs is not None:
        raise ValueError("method must not have vargargs on its signature")

    for i, arg in enumerate(args):
        # skiping args_spec.args[0] because it will be either self or cls ()
        kwargs[args_spec.args[i + 1]] = arg
    return kwargs


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


class GenericCache(object):
    '''
    Generic cache class, intented to be used as a helper for caching class or instance
    methods.

    Args:
        cache_backend (object): The cache backend to be used.
            Must be a backend.BaseBackend implementation.

        default_timeout (:obj:`int`, optional): Default timeout (in seconds) used
            in key creation.

        logging_enabled (bool): If logging is enabled, defaults to `False`

    Attributes:
        logger (logging.Logger): the logger instance used for logging.
        cache_backend (object): the cache backend to be used.
        default_timeout (int): Default timeout (in seconds) used in key creation.
        logging_enabled (bool): If logging is enabled, defaults to `False`
        key_prefix (str): A string to be preppended on each generated key. Defaults to ''.
    '''

    def __init__(
        self, cache_backend=BaseBackend(), default_timeout=None, logging_enabled=False,
        key_prefix='',
    ):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.cache_backend = cache_backend
        self.default_timeout = default_timeout
        self.logging_enabled = logging_enabled
        self.key_prefix = key_prefix

    def log(self, *args, **kwargs):
        '''
        Logs messages if `logging_enabled == True`.

        Attributes:
            log_level (int): the log level, defaults to `logging.DEBUG`. All other args
                and kwargs
            are forwarded to `logger.log` method.
        '''
        if not self.logging_enabled:
            return
        level = kwargs.pop('log_level', logging.DEBUG)
        self.logger.log(level, *args, **kwargs)

    def get_from_cache(self, key, **cache_kwargs):
        '''
        Returns the value for `key` from the cache backend. `key.key_str` will be used as
        the cache key. It is expected that `key` is a `BaseCacheKey` instance. Aditional
        cache kwargs will be forwarded to cache backend method `get`.
        '''
        return self.cache_backend.get(key.key_str, **cache_kwargs)

    def set(self, key, value, **cache_kwargs):
        '''
        Sets `value` for `key` on cache. `key.key_str` will be used as
        the cache key. It is expected that `key` is a `BaseCacheKey` instance. Aditional
        cache kwargs will be forwarded to cache backend method `set`. The `key.timeout`
        value will be used for timeout.
        '''
        self.log("set key={}".format(key))
        self.cache_backend.set(
            key.key_str, value, timeout=key.timeout, **cache_kwargs)

    def get(
        self, key, func, disable_cache=False, disable_cache_overwrite=False,
        **cache_kwargs
    ):
        '''
        Gets the value for `key`. It first tries to get the value from cache. If it
        can't will get the uncached value from `func`.

        Args:
            key (BaseCacheKey): the key to be queried on cache.
            func (function): a argumentless function that will be called if the uncached
                value is necessary. Used when the key is not cached or if cache is
                disabled.
            disable_cache (:obj:`bool`, optional): Defaults to `False`. If `True` the
                cache backend is not queried and the desired value is evaluated by calling
                `func()`.
            disable_cache_overwrite (:obj:`bool`, optional): Defaults to `False`. If
            `True` won't write to cache when value is evaluated by `func()`.
        '''
        value = None
        if not disable_cache:
            value = self.get_from_cache(key, **cache_kwargs)
            if value is None:
                self.log("cache miss for key={}".format(key))
            else:
                self.log("cache hit for key={}".format(key))

        if value is None:
            value = func()
            if not disable_cache_overwrite:
                self.set(key, value, **cache_kwargs)
        return value

    def flush(self, key, **cache_kwargs):
        '''
        Flushes (deletes) the key from the cache backend. It is expected that `key` is a
        `BaseCacheKey` instance. Aditional cache kwargs will be forwarded to cache backend
        method `delete`.
        '''
        self.log("flush key={}".format(key))
        return self.cache_backend.delete(key.key_str, **cache_kwargs)

    def get_key(self, key_type, *args, **kwargs):
        '''
        Generates a ArgsCacheKey based on the key_type, args and kwargs. This method
        may be overridden to better suits the use case needs.
        Args:
            key_type(`str`): The base key_type for ArgsCacheKey
        *args and **kwargs will be forward to ArgsCacheKey initializer.

        Returns:
            ArgsCacheKey: the generated key
        '''
        timeout = kwargs.pop('timeout', self.default_timeout)
        return ArgsCacheKey(
            self.key_prefix + key_type, timeout=timeout, *args, **kwargs
        )
