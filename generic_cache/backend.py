# Copyright (c) 2018, Globo.com (https://github.com/globocom)
#
# License: MIT

from datetime import datetime, timedelta


class BaseBackend(object):
    """
    Abstract class that acts like every Cache Backend Interface. Extend it
    to implement your own Cache Backend.
    """

    def get(self, key):
        raise NotImplementedError("Subclasses should implement this method")

    def set(self, key, value, timeout=None):
        raise NotImplementedError("Subclasses should implement this method")

    def delete(self, key):
        raise NotImplementedError("Subclasses should implement this method")


class InMemoryCache(BaseBackend):
    def __init__(self):
        self._cache = {}

    def get(self, key):
        now = datetime.now()
        value, expires_in = self._cache.get(key, (None, None))
        if expires_in is not None and expires_in < now:
            return None
        return value

    def set(self, key, value, timeout=None):
        expires_in = None
        if timeout is not None:
            expires_in = datetime.now() + timedelta(seconds=timeout)
        self._cache[key] = (value, expires_in)

    def delete(self, key):
        self._cache.pop(key, None)

    def print_cache(self):
        import pprint
        pprint.pprint(self._cache)
