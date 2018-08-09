import unittest
from ..cache import BaseCacheKey, ArgsCacheKey


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
