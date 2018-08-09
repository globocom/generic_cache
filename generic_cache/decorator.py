

class CacheDecorator(object):
    def __init__(self, key_prefix, cache_backend, key_builder, default_timeout=None):
        self._key_prefix = key_prefix
        self._cache_backend = cache_backend
        self._key_builder = key_builder
        self._default_timeout = default_timeout
        self._build_generic_cache()

    def __call__(self, key_type, key_timeout=None, key_version=""):
        if key_timeout == None:
            key_timeout = self._default_timeout
        return self._build_decorator(key_type, key_timeout, key_version)

    def _build_decorator(self, key_type, key_timeout, key_version):
        from functools import wraps
        def decorator(func):
            @wraps(func)
            def decorated(*args, **kwargs):
                disable_cache = kwargs.pop('disable_cache', False)
                disable_cache_overwrite = kwargs.pop(
                    'disable_cache_overwrite', False
                )

                def call_original():
                    return func(*args, **kwargs)

                key = self._build_key(key_type, func, *args, key_version=key_version, **kwargs)
                key.timeout = key_timeout
                return self._generic_cache.get(
                    key, call_original, disable_cache=disable_cache,
                    disable_cache_overwrite=disable_cache_overwrite
                )

            decorated.flush = self._flush
            return decorated
        return decorator

    def _build_generic_cache(self):
        from .cache import GenericCache
        self._generic_cache = GenericCache(
            self._cache_backend,
            self._default_timeout,
            key_prefix=self._key_prefix
        )

    def _build_key(self, key_type, original_func, *func_args, **func_kwargs):
        key_prefix = self._key_prefix + key_type
        return self._key_builder.build_key(key_prefix, original_func, *func_args, **func_kwargs)

    @staticmethod
    def _flush():
        pass

