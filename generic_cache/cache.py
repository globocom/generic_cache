import logging
from .backend import BaseBackend

__all__ = [
    'BaseCacheKey', 'ArgsCacheKey', 'GenericCache', 'GenericCacheMultiple',
    'generic_cached_method'
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

    @classmethod
    def key_from_normalized_method(cls, key_type, method, *methodargs, **methodkwargs):
        '''
        Given a method (instance or class method) will generate a key
        for the give method call. The generated key will be normalized. Meaning
        all method args are translated to kwargs.

        Args:
            method (function): the method in which the key will be built
            *methodargs: the args that will be called on the method, must not include
                self or cls
            *methodiwargs: the kwargs that will be called on the method

        Returns:
            ArgsCacheKey: the key resulted from the normalized
        '''

        kwargs = _get_method_kwargs(method, *methodargs, **methodkwargs)
        return cls(key_type, **kwargs)


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


class GenericCacheMultiple(GenericCache):
    '''
    An implementation of GenericCache that allows a single value to be cached by multiple
    keys, each with possibly different kwargs. One example case is a method
    `get_user(name=None, id=None)` where one might want to cache the same value for user
    with different timeouts for name and id.

    Example:
    >>> class CustomGeneric(GenericCacheMultiple):
    ...     def get_other_keys(self, key, value):
    ...         if key.key_type == 'get_user_by_id':
    ...             return [ArgsCacheKey('get_users_by_name', name=value.name)]
    ...         return []
    '''

    def get_other_keys(self, key, value):
        '''
        Based on a original key and the value for such key returns the other keys to be
        cached with such value. This method should be overriden.

        Args:
            key (BaseCacheKey): the base key.
            value (object): the value to be cached.

        Returns:
            list: The list of the other generated keys
        '''
        return []

    def get_keys(self, key, value):
        '''
        Returns a generator of keys to cache the value.

        Args:
            key (BaseCacheKey): the base key.
            value (object): the value to be cached.

        Returns:
            generator: a generator containing all keys to cache `value`
        '''
        yield key
        for k in self.get_other_keys(key, value):
            yield k

    def set(self, key, value, **cache_kwargs):
        '''
        Sets the value for all keys generated from the base key `key`. `get_keys`
        will be called with `key` and `value`.

        Args:
            key (BaseCacheKey): the base key to cache `value`
            value (object): the value to be cached
            **cache_kwargs: cache kwargs to be forward to cache backend
        '''
        for k in self.get_keys(key, value):
            super(GenericCacheMultiple, self).set(k, value, **cache_kwargs)

    def flush_keys(self, key, **cache_kwargs):
        '''
        Flush all keys generated base base key `key`. Because in order for all keys to be
        generated the cached value is necessary, the cache for `key` is cached first.
        If found the other keys are generated and each key is flushed.

        Args:
            key (BaseCacheKey): the base key to cache `value`
            **cache_kwargs: cache kwargs to be forward to cache backend
        '''
        value = self.get_from_cache(key, **cache_kwargs)
        if value is not None:
            for k in self.get_keys(key, value):
                self.flush(k, **cache_kwargs)


def generic_cached_method(key_type, key_timeout=None, cache_attr='generic_cache', key_version="", class_attr_keys=[]):
    '''
    Decorator to automatically cache methods from a class which has a GenericCache
    attribute. The decorated function must be e instance method or a classmethod
    which has an attribute (usually `generic_cache`) that is an instance of GenericCache.

    In order to get the generated cache key the `GenericCache.get_key` method will
    be called with `key_type=fname` where fname is the name of the decorated method.

    Example:
    >>> class MyCachedClass(object):
    ...     generic_cache = GenericCache(CacheBackend())
    ...
    ...     @generic_cached_method('some_key_type')
    ...     def my_cached_method(self):
    ...         import random
    ...         return random.random()

    Example with cache_attr:
    >>> class MyOtherCachedClass(object):
    ...     other_generic_cache = GenericCache(CacheBackend())
    ...
    ...     @generic_cached_method('my_key_type', cache_attr='other_generic_cache')
    ...     def my_cached_method(self):
    ...         import random
    ...         return random.random()

    Args:
        key_type (str): the key_type used to build the key
        timeout (:obj:`int`, optional): custom key timeout. Defaults to the generic cache
            timeout
        cache_attr (str): the name of the class attribute which holds the GenericCache
            instance
        cache_attr_keys (:list:`str`): A list of class attributes that should be used to
            create the key of this instance.
    '''
    from functools import wraps

    def decorator(method):

        @wraps(method)
        def decorated(instance, *args, **kwargs):
            disable_cache = kwargs.pop('disable_cache', False)
            disable_cache_overwrite = kwargs.pop(
                'disable_cache_overwrite', False)
            generic_cache = getattr(instance, cache_attr, None)
            if not isinstance(generic_cache, GenericCache):
                class_name = ''
                if isinstance(instance, type):
                    class_name = instance.__name__
                else:
                    class_name = instance.__class__.__name__
                raise ValueError(u"{}.{} is not an instance of GenericCache".format(
                    class_name, cache_attr
                ))

            def f():
                return method(instance, *args, **kwargs)

            _kwargs = kwargs.copy()
            class_attr_dict = dict((arg, getattr(instance, arg)) for arg in class_attr_keys)
            _kwargs.update(class_attr_dict)

            normalized_kwargs = _get_method_kwargs(
                method, *args, **_kwargs
            )
            key = generic_cache.get_key(key_type, key_version=key_version, **normalized_kwargs)
            if key_timeout is not None:
                key.timeout = key_timeout
            return generic_cache.get(
                key, f, disable_cache=disable_cache,
                disable_cache_overwrite=disable_cache_overwrite
            )
        return decorated
    return decorator
