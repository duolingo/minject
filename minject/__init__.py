"""
The Registry provides a simple form of dependency injection to streamline app initialization.

The Registry can be used to avoid having to add singletons to your code, which
makes testing and configuration significantly easier. Instead of hardcoding
into the source what objects need to reference each other and how they are
constructed, the Registry allows that information to be changed based on your
configuration or skipped entirely to make unit testing easier. In many ways
this is a primitive form of Dependency Injection or a Service Locator.

To use the registry, treat it as a dict to which you pass class types:

from minject import registry
my_registry = registry.initialize()
api = my_registry[MyApi]

If you want to pass init arguments to a registry managed object, then
use either the @inject.bind decorator on your class definition, or use
the inject.define function on an existing class.

@inject.bind(url='http://localhost')
class MyApi:
    def __init__(self, url): ...

class ColorClass:
    def __init__(self, color): ...
BlueClass = inject.define(ColorClass, color='blue')

You can also reference other registry managed objects in your calls to
bind or define by using the inject.reference function. This will instruct
the registry to find the given reference at init-time:

@inject.bind(api=inject.reference(MyApi), path='/index')
class MyResource:
    def __init__(self, api, path): ...

Registry will also store objects that are keyed by a simple string. You can
keep any value you want in the registry this way, but these objects will NOT
benefit from being automatically initialized (as registry does not know how
to do so). Simply treat Registry as a dictionary with string keys (this also
works with inject.reference):

registry['something_i_need'] = make_something()
something = registry['something_i_need']
"""

__version__ = "1.0.0"

from . import inject
from .inject_attrs import inject_define as define, inject_field as field
from .registry import Registry, initialize

__all__ = [
    "define",
    "field",
    "inject",
    "initialize",
    "Registry",
]
