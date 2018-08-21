import unittest
import mock
from generic_cache.cache import (
    GenericCache, BaseCacheKey, ArgsCacheKey,
)
from generic_cache.backend import BaseBackend, InMemoryCache


class MockedCachedBacked(BaseBackend):
    get = mock.Mock()
    set = mock.Mock()
    delete = mock.Mock()


class CacheBaseTestCase(unittest.TestCase):
    key_timeout = 10
    cache_key = BaseCacheKey('test_key', timeout=key_timeout)

    def tearDown(self):
        MockedCachedBacked.get.reset_mock()
        MockedCachedBacked.set.reset_mock()
        MockedCachedBacked.delete.reset_mock()


class TestGenericCache(CacheBaseTestCase):

    def test_attrs(self):
        generic = GenericCache()
        self.assertIsNotNone(generic.logger)
        self.assertIsInstance(generic.cache_backend, BaseBackend)
        self.assertIsNone(generic.default_timeout)
        self.assertIs(False, generic.logging_enabled)

    def test_get_from_cache(self):
        generic = GenericCache(MockedCachedBacked())
        value = generic.get_from_cache(self.cache_key)
        MockedCachedBacked.get.assert_called_with(self.cache_key.key_str)
        self.assertEqual(MockedCachedBacked.get.return_value, value)

    def test_get_with_cache(self):
        generic = GenericCache(MockedCachedBacked())
        value = generic.get(self.cache_key, lambda: "not cached")
        MockedCachedBacked.get.assert_called_with(self.cache_key.key_str)
        self.assertEqual(MockedCachedBacked.get.return_value, value)

    def test_get_with_cache_none(self):
        generic = GenericCache(MockedCachedBacked())
        MockedCachedBacked.get.return_value = None
        value = generic.get(self.cache_key, lambda: "not cached")
        self.assertEqual("not cached", value)
        MockedCachedBacked.set.assert_called_with(
            self.cache_key.key_str, value, timeout=self.key_timeout)

    def test_get_with_disable_cache(self):
        generic = GenericCache(MockedCachedBacked())
        value = generic.get(self.cache_key, lambda: "not cached", disable_cache=True)
        self.assertEqual("not cached", value)
        self.assertEqual(0, MockedCachedBacked.get.call_count)
        MockedCachedBacked.set.assert_called_with(
            self.cache_key.key_str, value, timeout=self.key_timeout)

    def test_get_with_disable_cache_and_disable_overwrite(self):
        generic = GenericCache(MockedCachedBacked())
        value = generic.get(
            self.cache_key, lambda: "not cached", disable_cache=True,
            disable_cache_overwrite=True
        )
        self.assertEqual("not cached", value)
        self.assertEqual(0, MockedCachedBacked.get.call_count)
        self.assertEqual(0, MockedCachedBacked.set.call_count)

    def test_flush(self):
        generic = GenericCache(MockedCachedBacked())
        generic.flush(self.cache_key)
        MockedCachedBacked.delete.assert_called_once_with(self.cache_key.key_str)

    def test_get_key(self):
        generic = GenericCache()
        key = generic.get_key('type', 1, 2, kw='kwarg')
        self.assertEqual('type__1__2__kw_kwarg', key.key_str)
        generic = GenericCache(key_prefix="MyCustomClass.")
        key = generic.get_key('type', 1, 2, kw='kwarg')
        self.assertEqual('MyCustomClass.type__1__2__kw_kwarg', key.key_str)


