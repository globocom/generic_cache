from datetime import datetime, timedelta


class BaseBackend(object):
    def get(self, key):
        return None

    def set(self, key, value, timeout=None):
        return None

    def delete(self, key):
        return None


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
