# __NO_RELICENSE__

import time
import cProfile

"""
from : https://zapier.com/engineering/profiling-python-boss/
Usage example:

@timefunc
def expensive_function():
    for x in get_number():
        i = x ^ x ^ x
    return 'some result!'

# prints "expensive_function took 0.72583088875 seconds"
result = expensive_function()
"""

def timefunc(f):
    def f_timer(*args, **kwargs):
        start = time.time()
        result = f(*args, **kwargs)
        end = time.time()
        print f.__name__, 'took', end - start, 'time'
        return result
    return f_timer

def get_number():
    for x in xrange(5000000):
        yield x


"""
@do_cprofile
def expensive_function():
    for x in get_number():
        i = x ^ x ^ x
    return 'some result!'
"""

def do_cprofile(func):
    def profiled_func(*args, **kwargs):
        profile = cProfile.Profile()
        try:
            profile.enable()
            result = func(*args, **kwargs)
            profile.disable()
            return result
        finally:
            profile.print_stats()
    return profiled_func

"""
@do_profile(follow=[get_number])
def expensive_function():
    for x in get_number():
        i = x ^ x ^ x
    return 'some result!'
"""
try:
    from line_profiler import LineProfiler

    def do_profile(follow=[]):
        def inner(func):
            def profiled_func(*args, **kwargs):
                try:
                    profiler = LineProfiler()
                    profiler.add_function(func)
                    for f in follow:
                        profiler.add_function(f)
                    profiler.enable_by_count()
                    return func(*args, **kwargs)
                finally:
                    profiler.print_stats()
            return profiled_func
        return inner

except ImportError:
    def do_profile(follow=[]):
        "Helpful if you accidentally leave in production!"
        def inner(func):
            def nothing(*args, **kwargs):
                return func(*args, **kwargs)
            return nothing
        return inner

def get_number():
    for x in xrange(5000000):
        yield x

@do_profile(follow=[get_number])
def expensive_function():
    for x in get_number():
        i = x ^ x ^ x
    return 'some result!'
