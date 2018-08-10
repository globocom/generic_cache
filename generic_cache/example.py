import random
import time
from .backend import InMemoryCache
from .decorator import CacheDecorator
from .key_builder import AttrsMethodKeyBuilder


cache_backend = InMemoryCache()
user_cache = CacheDecorator("UserModel.", cache_backend, AttrsMethodKeyBuilder(['id']))


class User(object):
    def __init__(self, id):
        self.id = id
    
    @user_cache("get_data")
    def get_data(self):
        time.sleep(3)
        return {"name": "Robert Paulson"}
    
    @user_cache("get_photo_url")
    def get_photo_url(self, photo_type):
        time.sleep(3)
        return "http://myphoto.who/{}/{}".format(self.id, photo_type)


def run_user_example():
    user1 = User('id_1')
    print "Getting user data, first time..."
    print user1.get_data()
    print
    time.sleep(1)
    print "Getting user data, cached"
    print user1.get_data()

    print
    print
    print
    time.sleep(1)
    print "Getting user photo avatar, first time..."
    print user1.get_photo_url("avatar")
    print
    time.sleep(1)
    print "Getting user data, cached"
    print user1.get_photo_url("avatar")

    print
    print
    print
    time.sleep(1)
    print "Getting user photo thumbnail, first time..."
    print user1.get_photo_url("thumbnail")
    print
    time.sleep(1)
    print "Getting user data, cached"
    print user1.get_photo_url("thumbnail")
    return user1