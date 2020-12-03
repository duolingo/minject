"""Helper classes used by the test_registry module.
These are placed in a separate file to make sure the namespace
is consistent when test_registry is called as __main__. If these
classes are in the same file then the registry gets confused because
they will all be in the `__main__` module instead of the expected
`tests.registry.test_registry` module.
"""

import abc

from six import with_metaclass

from duolingo_base.registry import inject


@inject.bind(name=inject.reference("name"))
class Named(object):
    def __init__(self, name):
        self.name = name


class Tagger(object):
    def __init__(self, tag=None):
        self.tag = tag


class TestType(object):
    pass


class Foo(object):
    pass


class Bar(Foo):
    pass


class Inner(object):
    def __init__(self, name):
        self.name = name


@inject.bind(name="outer", inner=inject.reference(Inner, name="inner"))
class Outer(object):
    def __init__(self, name, inner):
        self.name = name
        self.inner = inner


@inject.bind(url="http://localhost")
class Server(object):
    def __init__(self, url):
        self.url = url


@inject.bind(server=inject.reference(Server))
class AbstractResource(object):
    def __init__(self, server, path):
        self.server = server
        self.path = path


@inject.bind(path="/search.html")
class SearchResource(AbstractResource):
    pass


@inject.bind(url="http://localhost")
class AbstractApiClient(with_metaclass(abc.ABCMeta)):
    def __init__(self, url):
        self.url = url

    @abc.abstractmethod
    def get(self):
        pass


class MyApiClient(AbstractApiClient):
    def get(self):
        return self.url + "/myapi"


@inject.bind(width="1px", color="black")
class Border(object):
    def __init__(self, width, style, color):
        self.width = width
        self.style = style
        self.color = color


class FakeWorker(object):
    def __init__(self):
        FakeWorker.instance = self

    def start(self):
        self._started = True

    def close(self):
        self._closed = True


inject.start_method(FakeWorker, FakeWorker.start)
inject.close_method(FakeWorker, FakeWorker.close)


def logic(registry_impl):
    return registry_impl


def passthrough(*args, **kwargs):
    return (args, kwargs)


def nested(arg):
    return arg


class Factory(object):
    def create(self, value):
        return str(value)