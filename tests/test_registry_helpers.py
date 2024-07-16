"""Helper classes used by the test_registry module.
These are placed in a separate file to make sure the namespace
is consistent when test_registry is called as __main__. If these
classes are in the same file then the registry gets confused because
they will all be in the `__main__` module instead of the expected
`tests.registry.test_registry` module.
"""

import abc

from minject import inject


@inject.bind(name=inject.reference("name"))
class Named:
    def __init__(self, name):
        self.name = name


class Tagger:
    def __init__(self, tag=None):
        self.tag = tag


class TestType:
    pass


class Foo:
    pass


class Bar(Foo):
    pass


class Inner:
    def __init__(self, name):
        self.name = name


@inject.bind(name="outer", inner=inject.reference(Inner, name="inner"))
class Outer:
    def __init__(self, name, inner):
        self.name = name
        self.inner = inner


@inject.bind(url="http://localhost")
class Server:
    def __init__(self, url):
        self.url = url


@inject.bind(server=inject.reference(Server))
class AbstractResource:
    def __init__(self, server, path):
        self.server = server
        self.path = path


@inject.bind(path="/search.html")
class SearchResource(AbstractResource):
    pass


# Note: mypy enforces that the generic variable passed to a Type[T] be a concrete class
# whether it should do this is under debate, but the issue hasn't been fixed in four years so
# we just ignore it for now
# See: https://github.com/python/mypy/issues/5374
@inject.bind(url="http://localhost")  # type: ignore
class AbstractApiClient(metaclass=abc.ABCMeta):
    def __init__(self, url):
        self.url = url

    @abc.abstractmethod
    def get(self):
        pass


class MyApiClient(AbstractApiClient):
    def get(self):
        return self.url + "/myapi"


@inject.bind(width="1px", color="black")
class Border:
    def __init__(self, width, style, color):
        self.width = width
        self.style = style
        self.color = color


class FakeWorker:
    def __init__(self):
        FakeWorker.instance = self

    def close(self):
        self._closed = True


def logic(registry_impl):
    return registry_impl


def passthrough(*args, **kwargs):
    return (args, kwargs)


def nested(arg):
    return arg


class Factory:
    def create(self, value):
        return str(value)
