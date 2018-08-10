import unittest
from generic_cache.key_builder import BaseCacheKey, ArgsCacheKey


class TestBaseCacheKey(unittest.TestCase):
    def test_attrs(self):
        key = BaseCacheKey("mykey", timeout=5, key_version="v1")
        self.assertEqual(key.timeout, 5)
        self.assertEqual(key.version, "v1")
        self.assertEqual(key.key_type, "mykey")
        self.assertEqual(str(key), "mykeyv1")
        self.assertEqual(key.key_str, "mykeyv1")


class TestArgsCacheKey(unittest.TestCase):
    def test_attrs(self):
        key = ArgsCacheKey('type', 1, 2, 3, other='some', some='other')
        self.assertIsNone(key._key_str)
        self.assertEqual((1, 2, 3), key.args)
        self.assertEqual({'some': 'other', 'other': 'some'}, key.kwargs)

    def test_key_str(self):
        key = ArgsCacheKey('type', 1, 2, 3, some='other', other='some', key_version="v2")
        self.assertIsNone(key._key_str)
        key_str = key.key_str
        self.assertEqual(key_str, key._key_str)
        expeceted_key_str = "typev2__1__2__3__other_some__some_other"
        self.assertEqual(expeceted_key_str, key_str)


class BaseKeyBuilderTestCase(unittest.TestCase):
    def setUp(self):
        self.builder = self.get_builder()


class FunctionKeyBuilderTestCase(BaseKeyBuilderTestCase):
    def get_builder(self):
        from generic_cache.key_builder import FunctionKeyBuilder
        return FunctionKeyBuilder()

    def test_build_key_should_return_a_key_that_matches_args_and_kwargs(self):
        def sample_func(a, b, c):
            pass

        expected_key_str = 'sample__a_1__b_2__c_3'
        def _test_based_on_args(*args, **kwargs):
            key_str = self.builder.build_key('sample', sample_func, *args, **kwargs).key_str
            self.assertEqual(expected_key_str, key_str)

        _test_based_on_args(1, 2, 3)
        _test_based_on_args(1, 2, c=3)
        _test_based_on_args(1, b=2, c=3)
        _test_based_on_args(a=1, b=2, c=3)


class MethodKeyBuilderTestCase(BaseKeyBuilderTestCase):
    def get_builder(self):
        from generic_cache.key_builder import MethodKeyBuilder
        return MethodKeyBuilder()

    def test_key_str_should_ignore_self_args(self):
        class Sample(object):
            def sample_method(self, a, b=2):
                pass

        s = Sample()
        expected_key_str = 'sample__a_1__b_2'
        def _test_based_on_args(*args, **kwargs):
            key_str = self.builder.build_key('sample', s.sample_method, s, *args, **kwargs).key_str
            self.assertEqual(expected_key_str, key_str)

        _test_based_on_args(1, 2)
        _test_based_on_args(1, b=2)


class AttrsMethodKeyBuilderTestCase(BaseKeyBuilderTestCase):
    def get_builder(self):
            from generic_cache.key_builder import AttrsMethodKeyBuilder
            return AttrsMethodKeyBuilder(['id'])
    
    def test_key_str_should_include_passed_args(self):
        class Sample(object):
            id = 'uniq'
            def sample_method(self, a):
                pass
            
        s = Sample()
        expected_key_str = 'sample__a_1__id_uniq'
        key_str = self.builder.build_key('sample', s.sample_method, s, 1).key_str
        self.assertEqual(expected_key_str, key_str)
        
