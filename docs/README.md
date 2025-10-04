[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/pyiron/pyiron_snippets/HEAD)
[![License](https://img.shields.io/badge/License-BSD_3--Clause-blue.svg)](https://opensource.org/licenses/BSD-3-Clause)
[![Coverage Status](https://codecov.io/gh/pyiron/pyiron_snippets/graph/badge.svg)](https://codecov.io/gh/pyiron/pyiron_snippets)
[![Documentation Status](https://readthedocs.org/projects/pyiron-snippets/badge/?version=latest)](https://pyiron-snippets.readthedocs.io/en/latest/?badge=latest)

[![Anaconda](https://anaconda.org/conda-forge/pyiron_snippets/badges/version.svg)](https://anaconda.org/conda-forge/pyiron_snippets)
[![Last Updated](https://anaconda.org/conda-forge/pyiron_snippets/badges/latest_release_date.svg
)](https://anaconda.org/conda-forge/pyiron_snippets)
[![Platform](https://anaconda.org/conda-forge/pyiron_snippets/badges/platforms.svg)](https://anaconda.org/conda-forge/pyiron_snippets)
[![Downloads](https://anaconda.org/conda-forge/pyiron_snippets/badges/downloads.svg)](https://anaconda.org/conda-forge/pyiron_snippets)

# pyiron_snippets

This is a collection of independent python snippets which we in the pyiron project find generically useful.

To qualify for inclusion, a snippet must not have any dependencies outside the python standard library, and should fit reasonably inside a single file.

(Note that the _tests_ may have non-standard dependencies, e.g. to ensure the snippets work in various edge cases we care about, but the actual snippets themselves must be able to behave well in a clean environment.)


# Summary

Note that each snippet may have more functionality than shown in this readme -- taking a look at the source code and test suite is the best way to get an exhaustive sense of their capability -- but these examples will give you a sense of when each snippet is useful.

## Colors

Just a shortcut to the `seaborn.color_palette()` of colors in hex:

```python
>>> from pyiron_snippets import colors
>>> colors.SeabornColors.white
'#ffffff'

```

## Deprecate

Easily indicate that some functionality is being deprecated

```python
>>> from pyiron_snippets import deprecate
>>>
>>> @deprecate.deprecate(message="Use `bar(a, b)` instead", version="0.5.0")
... def foo(a, b):
...     pass
>>> 
>>> foo(1, 2)

```

Raises a warning like `DeprecationWarning: __main__.foo is deprecated: Use bar(a, b) instead. It is not guaranteed to be in service in vers. 0.5.0 foo(1, 2)`


## DotDict

A dictionary that allows dot-access. Has `.items()` etc.

```python
>>> from pyiron_snippets import dotdict
>>>
>>> d = dotdict.DotDict({"a": 1})
>>> d.b = 2
>>> print(d.a, d.b)
1 2

```

## Exception context

A variant of [`contextlib.ExitStack`](https://docs.python.org/3/library/contextlib.html#contextlib.ExitStack) that only executes registered callbacks when an exception is raised, and only if that exception matches one of the specified exception types (or any exception, if types are not specified).

```python
>>> from pyiron_snippets import exception_context
>>>
>>> def its_historical(history: list[str], message: str) -> None:
...     history.append(message)
>>>
>>> history = []
>>> try:
...     with exception_context.ExceptionExitStack(RuntimeError) as stack:
...         _ = stack.callback(its_historical, history, "with matching type")
...         raise RuntimeError("Application error")
... except RuntimeError:
...     history
['with matching type']

>>> history = []
>>> try:
...     with exception_context.ExceptionExitStack(TypeError, ValueError) as stack:
...         _ = stack.callback(its_historical, history, "with mis-matching types")
...         raise RuntimeError("Application error")
... except RuntimeError:
...     history
[]

```

The module also provides a wrapper, `on_error`, which provides a more compact interface if you only have a single callback function (as in the examples above):

```python
>>> from pyiron_snippets import exception_context
>>>
>>> def its_historical(history: list[str], message: str) -> None:
...     history.append(message)
>>>
>>> history = []
>>>
>>> try:
...     with exception_context.on_error(
...         its_historical, 
...         RuntimeError, 
...         history,
...         "a more compact single-callback interface",
...     ):
...         raise RuntimeError("Application")
... except RuntimeError:
...     history
['a more compact single-callback interface']

```

## Factory

Make dynamic classes that are still pickle-able

```python
>>> from abc import ABC
>>> import pickle
>>>
>>> from pyiron_snippets import factory
>>>
>>> class HasN(ABC):
...     '''Some class I want to make dynamically subclass.'''
...     def __init_subclass__(cls, /, n=0, s="foo", **kwargs):
...         super(HasN, cls).__init_subclass__(**kwargs)
...         cls.n = n
...         cls.s = s
...
...     def __init__(self, x, y=0):
...         self.x = x
...         self.y = y
>>>
>>> @factory.classfactory
... def has_n_factory(n, s="wrapped_function", /):
...     return (
...         f"{HasN.__name__}{n}{s}",  # New class name
...         (HasN, ),  # Base class(es)
...         {},  # Class attributes dictionary
...         {"n": n, "s": s}
...  # dict of `builtins.type` kwargs (passed to `__init_subclass__`)
...     )
>>>
>>> Has2 = has_n_factory(2, "my_dynamic_class")
>>>
>>> foo = Has2(42, y=-1)
>>> print(foo.n, foo.s, foo.x, foo.y)
2 my_dynamic_class 42 -1
>>> reloaded = pickle.loads(pickle.dumps(foo))  # doctest: +SKIP
>>> print(reloaded.n, reloaded.s, reloaded.x, reloaded.y)  # doctest: +SKIP
2 my_dynamic_class 42 -1  # doctest: +SKIP

```

(Pickle doesn't play well with testing the docs -- you can't run `pickle.dumps(pickle.loads(5))` either!)


## Files

Shortcuts for filesystem manipulation

```python
>>> from pyiron_snippets import files
>>>
>>> d = files.DirectoryObject("some_dir")
>>> d.write(file_name="my_filename.txt", content="Some content")
>>> d.file_exists("my_filename.txt")
True
>>> d.delete()

```


## Has post

A meta-class introducing a `__post__` dunder which runs after the `__init__` of _everything_ in the MRO.

```python
>>> from pyiron_snippets import has_post
>>>
>>> class Foo(metaclass=has_post.HasPost):
...     def __init__(self, x=0):
...         self.x = x
...         print(f"Foo.__init__: x = {self.x}")
>>>
>>> class Bar(Foo):
...     def __init__(self, x=0, post_extra=2):
...         super().__init__(x)
...         self.x += 1
...         print(f"Bar.__init__: x = {self.x}")
...
...     def __post__(self, *args, post_extra=2, **kwargs):
...         self.x += post_extra
...         print(f"Bar.__post__: x = {self.x}")
>>>
>>> Bar().x
Foo.__init__: x = 0
Bar.__init__: x = 1
Bar.__post__: x = 3
3

```

Honestly, try thinking if there's another way to solve your problem; this is a dark magic.

## Import alarm

Fail gracefully when optional dependencies are missing for (optional) functionality.

```python
>>> from pyiron_snippets import import_alarm
>>>
>>> with import_alarm.ImportAlarm(
...     "Some functionality unavailable: `magic` dependency missing"
... ) as my_magic_alarm:
...     import magic
>>>
>>> with import_alarm.ImportAlarm("This warning won't show up") as datetime_alarm:
...     import datetime
>>>
>>> class Foo:
...     @my_magic_alarm
...     @datetime_alarm
...     def __init__(self, x):
...         self.x = x
...
...     @property
...     def magical(self):
...         return magic.method(self.x)
...
...     def a_space_odyssey(self):
...         print(datetime.date(2001, 1, 1))
>>>
>>> foo = Foo(0)
>>>  # Raises a warning re `magic` (since that does not exist)
>>>  # but not re `datetime` (since it does and we certainly have it)
>>> foo.a_space_odyssey()
2001-01-01

>>> try:
...     foo.magical(0)
... except NameError as e:
...     print("ERROR:", e)
ERROR: name 'magic' is not defined

```

## Logger

Configures the logger and writes to `pyiron.log`

## Retrieve

Tools for retrieving objects from strings.
Particularly useful when objects or references are serialized by reference to their library location.

```python
>>> from pyiron_snippets import retrieve
>>> ThreadPoolExecutor = retrieve.import_from_string(
...     "concurrent.futures.ThreadPoolExecutor"
... )
>>> with ThreadPoolExecutor(max_workers=2) as executor:
...     future = executor.submit(pow, 2, 3)
...     print(future.result())
8

```
   
Includes an extra tool, `get_importable_string_from_string_reduction` for singleton-pattern string reductions.     

## Retry

If at first you don't succeed

```python
>>> from time import time
>>>
>>> from pyiron_snippets import retry
>>>
>>> def at_most_three_seconds():
...     t = int(time())
...     if t % 3 != 0:
...         raise ValueError("Not yet!")
...     return t
>>>
>>> retry.retry(at_most_three_seconds, msg="Tried and failed...", error=ValueError) % 3
0

```

Depending on the system clock at invokation, this simple example may give warnings like `UserWarning: Tried and failed... Trying again in 1.0s. Tried 1 times so far...` up to two times.


## Singleton

A metaclass for the [singleton pattern](https://en.wikipedia.org/wiki/Singleton_pattern).

```python
>>> from pyiron_snippets import singleton
>>>
>>> class Foo(metaclass=singleton.Singleton):
...     pass
>>>
>>> foo1 = Foo()
>>> foo2 = Foo()
>>> foo1 is foo2
True

```
