# Welcome to Generic Cache

ATTENTION: This is still a work in progress documentation.

This library is intended to ease caching the results of functions or method calls.

## TL;DR

Basically this library offers a decorator factory for you to use in your functions.
Then generic_cache will handle key creation and cache lookup for you.

#### Example
```python
import time
from generic_cache.decorator import CacheDecorator
from generic_cache.key_builder import AttrsMethodKeyBuilder

cache_backend = #... More on this below
cache_decorator = CacheDecorator("SummerCache.", cache_backend, AttrsMethodKeyBuilder(['id_number']))

class Summer:
    def __init__(self, id_number, dummy='dummy'):
        self.id_number = id_number
        self.dummy = dummy
    
    @cache_decorator("long_id_sum_cache")
    def long_id_sum(self, other_number):
        time.sleep(5)
        return self.id_number + other_number

summer = Summer(42)

# Long 5 secs wait for 43 result
result = summer.long_id_sum(1)

# Cached 43 result
result = summer.long_id_sum(1)

# Still Cached, it doesn't care about new instances.
result = Summer(42).long_id_sum(1)
```

## What Generic Cache differs from Python functools LRU Cache?

The major difference is that you can program your own cache Backend.
Python functools [native cache](https://docs.python.org/3/library/functools.html#functools.lru_cache) uses LRU policy.
So, if you would like to have, for example,  a cache that uses a Heap Tree you can
create it by simply extending [BaseBackend](https://github.com/globocom/generic_cache/blob/master/generic_cache/backend.py#L8) class
and pass it to the cache decorator.

## Glad you are still here, let's dive deeper!

To instantiate a decorator you will need 3 things:

1. A key_prefix which is a string that will be used to generate ao keys created by the decorator
1. a cache_backend. This could be any cache api that follows the implementation of `generic_cache.backend.BaseBackend` (it is based on django cache api, but not restricted to it)
1. A key builder (you can grab one of the key builders available at `generic_cache.key_builder` or build one that suits your needs)

To use the decorator you will also need to pass the key_type (`"long_id_sum_cache"` in previous example). This will also be used to build the key.

Once this three demands are satisfied you're ready to start caching.

In our previous example we used `AttrsMethodKeyBuilder`. This key_builder will build keys based on the name/values
of the method arguments plus the name/values of a set of the instance attributes.
So, from above, when we do:
```python
result = summer.long_id_sum(1)
```
the steps taken to evaluate the function is:
1. Build the key (in this case the final key built will be the string `"SummerCache.long_id_sum_cache__other_number_1__id_42")
1. Use the cache_backend to get a value from the cache.
1. If a value is found return the cached value
1. If no value is found. Call the actual function.
1. Cache the value with the built key.
1. Return the value

As you could see `AttrsMethodKeyBuilder` uses the methods arguments and instance attributes to build its keys. Other
key builders might be better for one's use case. `generic_cache` ships also with `MethodKeyBuilder` which only considers
the method arguments and `FunctionKeyBuilder`, which is analogous, but intended to use on functions not class/instance methods.

#### Example of how `AttrsMethodKeyBuilder` works
```python
summer = Summer(1)

# Not cached
summer.long_id_sum(1)

# Cached
summer.long_id_sum(1)

# Not Cached, changed argument value
summer.long_id_sum(2)

# Cached
summer.long_id_sum(2)

same_summer = Summer(1)
# Cached
same_summer.long_id_sum(1)

other_summer = Summer(2)

# Not cached, attribute `id_number` is different.
other_summer.long_id_sum(1)

different_but_same_summer = Summer(1, 'other_dummy_value')

# Cached. dummy attribute changed, but is not used for key building.
different_but_same_summer.long_id_sum(1)
```

You can use the same decorator on multiple functions.
```python
class Example:
    @cache_dec("method")
    def method(self):
        # ....

    @cache_dec("other_method")
    def other_method(self):
        # ....
```

## Key management
> There are only two hard things in Computer Science: cache invalidation and naming things.
>
> -- Phil Karlton

`generic_cache` comes with a handful of tools for cache invalidation.

### Timeouts
`CacheDecorator` accepts a `default_timeout` argument which will be used on all its created keys.
```python
cache_decorator = CacheDecorator("SummerCache.", cache_backend, AttrsMethodKeyBuilder(['id_number']), default_timeout=1000)
```

When decorating a function you can also set a `key_timeout`. Which will be used to all keys built on that function.
```python
@cache_decorator("my_func_cache", key_timeout=1500)
def my_func():
    pass
```

### Key Versions
Now suppose you have this function
```python
@cache_decorator("sum_a_number", timeout=1000)
def sum_a_number(other_number):
    return 1 + other_number
```

And its implementation has now changed to:
```python
def sum_a_number(other_number):
    return 10 + other_number
```
This implementation change affects the return value of the function, but you will probably have cached values of the previous implementation.
The secret is to use key_versions when this happens:

```python
@cache_decorator("sum_a_number", timeout=1000, key_version="v1.1")
def sum_a_number(other_number):
    return 10 + other_number
```

Now every generated key will have the version appendend. Which won't cause the cache to lookup old implementation keys. If the implementation
changes again. Just bump the key_version.

### Flushing
Suppose you have a `User` class which caches the result of `get_photo`:

```python
class User:
    def __init__(self, id):
        self.id = id

    @cache_decorator("get_photo")
    def get_photo(self, photo_type):
        # Implementation...

user = User('user_id_1')
# Happily using my cached function!
photo = user.get_photo('avatar')
```

Now somewhere in your system there is an upload in your user photo avatar and you know you must invalidate cache.
Thankfully `CacheDecorator` will enhance the function with a `cache` attribute that you can use to `flush` the cached value.
```python
user = User('user_id_1')
# Cached
user.get_photo('avatar')

# Somewhere after a new photo is uploaded

# You call the flush method with the same arguments you would call the cached function.
# WARNING for class/instance methods will you have to pass the class/instance as the first argument
user.get_photo.cache.flush(user, 'avatar')

# No longer cached
user.get_photo('avatar')
```

### Disabling Cache
Every cached function will accept a `disable_cache` kwarg. If this value is `True` the function will always be evaluated, ignoring cache lookups.

There is also the `disable_cache_overwrite` which forces the cache not to be updated on that call.
