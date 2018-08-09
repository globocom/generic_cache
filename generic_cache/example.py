import random
from .cache import GenericCache, GenericCacheMultiple, generic_cached_method, ArgsCacheKey
from .backend import InMemoryCache


class Random(object):
    generic_cache = GenericCache(InMemoryCache())

    @generic_cached_method()
    def get_n(self, *args, **kwargs):
        return random.random()

    @classmethod
    @generic_cached_method()
    def get_n_class(cls, *args, **kwargs):
        return random.random()


class MultipleCache(GenericCacheMultiple):
    def get_other_keys(self, key, value):
        return [ArgsCacheKey(key.key_type, other='other', timeout=10, *key.args, **key.kwargs)]


class RandomMultiple(Random):
    generic_cache = MultipleCache(InMemoryCache())


class RandomOtherName(object):
    other_generic_cache = GenericCache(InMemoryCache())

    @generic_cached_method(cache_attr='other_generic_cache')
    def get_n(self, *args, **kwargs):
        return random.random()
