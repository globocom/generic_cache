import unittest
import mock
from generic_cache.cache import (
    GenericCache, GenericCacheMultiple, BaseCacheKey, generic_cached_method, ArgsCacheKey,
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


class CustomGenericCacheMultiple(GenericCacheMultiple):
    def get_other_keys(self, key, value):
        return [BaseCacheKey("other", timeout=20)]


class TestGenericCacheMultiple(CacheBaseTestCase):
    def test_get_keys(self):
        generic = CustomGenericCacheMultiple()
        keys = list(generic.get_keys(self.cache_key, None))
        self.assertEqual(2, len(keys))
        self.assertEqual(10, keys[0].timeout)
        self.assertEqual(20, keys[1].timeout)
        self.assertEqual("other", keys[1].key_str)

    def test_set(self):
        generic = CustomGenericCacheMultiple(MockedCachedBacked())
        generic.set(self.cache_key, "new_value", some_cache_kw="dummy")
        keys = list(generic.get_keys(self.cache_key, None))
        for key in keys:
            MockedCachedBacked.set.assert_any_call(
                key.key_str, "new_value", timeout=key.timeout, some_cache_kw="dummy"
            )

    def test_flush_keys(self):
        generic = CustomGenericCacheMultiple(MockedCachedBacked())
        MockedCachedBacked.get.return_value = mock.Mock()
        generic.flush_keys(self.cache_key, some_cache_kw="dummy")
        keys = list(generic.get_keys(self.cache_key, None))
        for key in keys:
            MockedCachedBacked.delete.assert_any_call(
                key.key_str, some_cache_kw="dummy"
            )

    def test_flush_keys_none_value(self):
        generic = CustomGenericCacheMultiple(MockedCachedBacked())
        MockedCachedBacked.get.return_value = None
        generic.flush_keys(self.cache_key, some_cache_kw="dummy")
        self.assertEqual(0, MockedCachedBacked.delete.call_count)


class GenericCached(object):
    generic_cache = GenericCache(InMemoryCache())
    multiple_generic_cache = CustomGenericCacheMultiple(InMemoryCache())
    mocked_generic_cache = GenericCache(MockedCachedBacked())
    lyst = [1, 2, 3, 4]

    @generic_cached_method('get_first')
    def get_first(self):
        return self.lyst[0]

    @generic_cached_method('get_second_key', cache_attr='multiple_generic_cache')
    def get_second(self):
        return self.lyst[1]

    @generic_cached_method('get_third', cache_attr='wrong_generic_cache')
    def get_third(self):
        return self.lyst[2]

    @generic_cached_method('normalized_args_test', key_timeout=10)
    def normalized_args_test(self, a, b, c):
        return a + b + c

    @generic_cached_method('timeout_test', key_timeout=10, cache_attr='mocked_generic_cache')
    def timeout_test(self, a):
        return a

    @generic_cached_method('timeout_test', key_version=3, cache_attr='mocked_generic_cache')
    def version_test(self, a):
        return a


class TesteGenericCachedMethod(CacheBaseTestCase):
    def test_method(self):
        instance = GenericCached()
        value = instance.get_first()
        self.assertEqual(1, value)

        instance.lyst = [2, 3, 4]
        cached_value = instance.get_first()
        self.assertEqual(1, cached_value)

        new_value = instance.get_first(disable_cache=True)
        self.assertEqual(2, new_value)

    def test_multiple_keys(self):
        instance = GenericCached()
        value = instance.get_second()
        self.assertEqual(2, value)
        self.assertEqual(
            2,
            len(instance.multiple_generic_cache.cache_backend._cache.keys())
        )

        instance.lyst = [2, 3, 4]
        cached_value = instance.get_second()
        self.assertEqual(2, cached_value)

        new_value = instance.get_second(disable_cache=True)
        self.assertEqual(3, new_value)

    def test_value_error(self):
        instance = GenericCached()
        self.assertRaises(ValueError, instance.get_third)

    def test_normalized_args(self):
        instance = GenericCached()
        instance.normalized_args_test(1, 2, c=3)
        expected_key = ArgsCacheKey(
            'normalized_args_test', a=1, b=2, c=3
        )
        cached_value = instance.generic_cache.get_from_cache(expected_key)
        self.assertEqual(6, cached_value)

    def test_custom_timeout(self):
        instance = GenericCached()
        instance.timeout_test(1)
        expected_key = ArgsCacheKey(
            'timeout_test', a=1, timeout=10
        )
        MockedCachedBacked.set.assert_called_with(
            str(expected_key), 1, timeout=expected_key.timeout
        )

    def test_custom_version(self):
        instance = GenericCached()
        instance.version_test(1)
        expected_key = ArgsCacheKey(
            'timeout_test', a=1, key_version=3
        )
        MockedCachedBacked.set.assert_called_with(
            str(expected_key), 1, timeout=None
        )
