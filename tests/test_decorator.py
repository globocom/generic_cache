import mock
import unittest

from generic_cache.decorator import CacheDecorator
from generic_cache.backend import InMemoryCache, BaseBackend
from generic_cache.key_builder import MethodKeyBuilder, ArgsCacheKey


class DecoratorTestCase(unittest.TestCase):
    def setUp(self):
        self.key_prefix = "Test"
        self.cache_backend = mock.Mock()
        self.key_builder = self.get_key_builder()
        self.default_timeout = 15
        self.decorator = self.get_decorator()

    def get_decorator(self):
        return CacheDecorator(
            self.key_prefix, self.cache_backend, self.key_builder, self.default_timeout
        )

    def get_key_builder(self):
        from generic_cache.key_builder import FunctionKeyBuilder
        return FunctionKeyBuilder()

    def test_decorator_should_set_a_flush_function_on_the_function(self):
        @self.decorator("hey")
        def _decorated_fun(self, ha):
            pass

        _decorated_fun.flush()

    def test_decorator_factory_should_have_the_following_attributes(self):
        self.assertEqual(self.key_prefix, self.decorator._key_prefix)
        self.assertEqual(self.cache_backend, self.decorator._cache_backend)
        self.assertEqual(self.key_builder, self.decorator._key_builder)
        self.assertEqual(self.default_timeout, self.decorator._default_timeout)

    @mock.patch('generic_cache.cache.GenericCache', autospec=True)
    def test_build_generic_cache(self, mock_generic):
        self.decorator._build_generic_cache()
        self.assertEqual(self.decorator._generic_cache, mock_generic.return_value)
        mock_generic.assert_called_once_with(
           self.cache_backend,
           self.default_timeout,
           key_prefix=self.key_prefix 
        )

    def test_build_key_should_use_key_builder(self):
        with mock.patch.object(self.key_builder, 'build_key', autospec=True) as mock_build_key:
            key = self.decorator._build_key('mykey', 1, 2, 3, hey='two')
            self.assertEqual(mock_build_key.return_value, key)
            mock_build_key.assert_called_once_with(self.key_prefix + 'mykey', 1, 2, 3, hey='two')


class MockedCachedBacked(BaseBackend):
    get = mock.Mock(return_value=None)
    set = mock.Mock()
    delete = mock.Mock()


cache_backend = InMemoryCache()
mocked_cache_backend = MockedCachedBacked()
key_builder = MethodKeyBuilder()
cache_dec = CacheDecorator("Test.", cache_backend, key_builder)
mocked_cache_dec = CacheDecorator("Test.", mocked_cache_backend, key_builder)


class GenericCached(object):
    lyst = [1, 2, 3, 4]

    @cache_dec('get_first')
    def get_first(self):
        return self.lyst[0]

    @cache_dec('normalized_args_test', key_timeout=10)
    def normalized_args_test(self, a, b, c):
        return a + b + c

    @mocked_cache_dec('timeout_test', key_timeout=10)
    def timeout_test(self, a):
        return a

    @mocked_cache_dec('version_test', key_version=3)
    def version_test(self, a):
        return a


class TesteGenericCachedMethod(unittest.TestCase):
    def test_method(self):
        instance = GenericCached()
        value = instance.get_first()
        self.assertEqual(1, value)

        instance.lyst = [2, 3, 4]
        cached_value = instance.get_first()
        self.assertEqual(1, cached_value)

        new_value = instance.get_first(disable_cache=True)
        self.assertEqual(2, new_value)

    def test_normalized_args(self):
        instance = GenericCached()
        instance.normalized_args_test(1, 2, c=3)
        expected_key = ArgsCacheKey(
            'Test.normalized_args_test', a=1, b=2, c=3
        )
        cached_value = cache_backend.get(expected_key.key_str)
        self.assertEqual(6, cached_value)

    def test_custom_timeout(self):
        instance = GenericCached()
        instance.timeout_test(1)
        expected_key = ArgsCacheKey(
            'Test.timeout_test', a=1, timeout=10
        )
        MockedCachedBacked.set.assert_called_with(
            str(expected_key), 1, timeout=expected_key.timeout
        )

    def test_custom_version(self):
        instance = GenericCached()
        instance.version_test(1)
        expected_key = ArgsCacheKey(
            'Test.version_test', a=1, key_version=3
        )
        MockedCachedBacked.set.assert_called_with(
            str(expected_key), 1, timeout=None
        )