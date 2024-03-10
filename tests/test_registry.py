import unittest
from typing import Sequence

import tests.test_registry_helpers as helpers
from minject.inject import (
    _RegistryConfig,
    _RegistryFunction,
    _RegistryNestedConfig,
    _RegistryReference,
    bind,
    config,
    define,
    function,
    reference,
    self_tag,
)
from minject.metadata import RegistryMetadata
from minject.mock import mock
from minject.model import Resolvable
from minject.registry import initialize


class _Super:
    """An empty superclass type."""


class _Sub(_Super):
    """An empty sub-class type."""


class RegistryTestCase(unittest.TestCase):
    def setUp(self):
        self.registry = initialize()

    def test_by_name(self) -> None:
        obj_a = object()
        obj_b = object()

        self.assertNotIn("a", self.registry)
        self.assertNotIn("b", self.registry)
        self.assertIsNone(self.registry.get("a"))
        with self.assertRaises(KeyError):
            self.registry["a"]  # pylint: disable=pointless-statement

        self.registry.register(obj_a, name="a")
        self.registry.register(obj_b, "b")

        self.assertIn("a", self.registry)
        self.assertIn("b", self.registry)
        self.assertEqual(obj_a, self.registry.get("a"))
        self.assertEqual(obj_b, self.registry.get("b"))
        self.assertEqual(obj_a, self.registry["a"])
        self.assertEqual(obj_b, self.registry["b"])

    def test_by_definition(self) -> None:
        self.assertNotIn(helpers.TestType, self.registry)
        self.assertIsNone(self.registry.get(helpers.TestType))

        test_obj = self.registry[helpers.TestType]
        self.assertIsInstance(test_obj, helpers.TestType)
        self.assertIs(test_obj, self.registry.get(helpers.TestType))

    def test_bindings(self) -> None:
        self.registry["name"] = "my_name"

        self.assertNotIn(helpers.Named, self.registry)

        named_obj = self.registry[helpers.Named]
        self.assertIsInstance(named_obj, helpers.Named)

        self.assertIs(named_obj, self.registry.get(helpers.Named))

        self.assertEqual("my_name", named_obj.name)

    def test_inheritance(self) -> None:
        bar = self.registry[helpers.Bar]

        self.assertIs(bar, self.registry[helpers.Bar])
        self.assertIs(bar, self.registry[helpers.Foo])
        self.assertIsNone(self.registry.get(object))

    def test_different_bindings(self) -> None:
        TaggerA = define(helpers.Tagger, tag="a")
        TaggerB = define(helpers.Tagger, tag="b")
        TaggerNone = define(helpers.Tagger)
        TaggerAref = define(helpers.Tagger, tag=reference("a"))

        self.registry["a"] = "a (ref)"

        a = self.registry[TaggerA]
        b = self.registry[TaggerB]
        none = self.registry[TaggerNone]
        aref = self.registry[TaggerAref]

        self.assertIs(a, self.registry[TaggerA])
        self.assertIsNot(a, b)
        self.assertIsNot(a, none)
        self.assertIsNot(a, aref)

        self.assertIs(b, self.registry[TaggerB])
        self.assertIsNot(b, none)
        self.assertIsNot(b, aref)

        self.assertIs(none, self.registry[TaggerNone])
        self.assertIsNot(none, aref)

        self.assertIs(aref, self.registry[TaggerAref])

    def test_nested_bind(self) -> None:
        outer = self.registry[helpers.Outer]

        self.assertEqual("outer", outer.name)
        self.assertIsNotNone(outer.inner)
        self.assertEqual("inner", outer.inner.name)

        self.assertIs(outer, self.registry[helpers.Outer])
        self.assertIs(outer.inner, self.registry[helpers.Inner])

    def test_bind_inherit(self) -> None:
        IndexResource = define(helpers.AbstractResource, path="/index.html")
        index = self.registry[IndexResource]

        self.assertEqual("/index.html", index.path)
        self.assertIsNotNone(index.server)
        self.assertEqual("http://localhost", index.server.url)
        self.assertIs(helpers.AbstractResource, index.__class__)
        self.assertIs(helpers.Server, index.server.__class__)

        AboutResource = define(helpers.AbstractResource, path="/about.html")
        about = self.registry[AboutResource]

        self.assertEqual("/about.html", about.path)
        self.assertIsNotNone(about.server)
        self.assertEqual("http://localhost", about.server.url)
        self.assertIs(helpers.AbstractResource, about.__class__)
        self.assertIsNot(index, about)
        self.assertIs(index.server, about.server)

        with self.assertRaises(TypeError):  # TODO raise something else
            self.registry[helpers.AbstractResource]  # pylint: disable=pointless-statement

        self.assertIs(index.server, self.registry[helpers.Server])

        UndefResource = define(helpers.AbstractResource)
        with self.assertRaises(TypeError):
            self.registry[UndefResource]  # pylint: disable=pointless-statement

        search = self.registry[helpers.SearchResource]

        self.assertEqual("/search.html", search.path)
        self.assertIsNotNone(search.server)
        self.assertEqual("http://localhost", search.server.url)
        self.assertIsNot(index, search)
        self.assertIs(index.server, search.server)

        Resource = define(
            helpers.AbstractResource,
            path="/index.html",
            server=reference(helpers.Server, url="http://example.com"),
        )
        resource = self.registry[Resource]

        self.assertEqual("/index.html", resource.path)
        self.assertIsNotNone(resource.server)
        self.assertEqual("http://example.com", resource.server.url)
        self.assertIsNot(index, resource)
        self.assertIsNot(index.server, resource.server)

    def test_nonbound_abstract(self) -> None:
        client = self.registry[helpers.MyApiClient]

        self.assertEqual("http://localhost/myapi", client.get())

    def test_config(self) -> None:
        RedBorder = define(helpers.Border, color="red")
        RedBorder.name = "border_red"

        DottedBorder = define(helpers.Border)
        DottedBorder.name = "border_dotted"

        self.registry.config.from_dict(
            {
                "registry": {
                    "by_class": {"tests.test_registry_helpers.Border": {"style": "solid"}},
                    "by_name": {
                        "border_red": {"width": "2px"},
                        "border_dotted": {"style": "dotted"},
                    },
                }
            }
        )

        border = self.registry[helpers.Border]
        border_red = self.registry[RedBorder]
        border_dotted = self.registry[DottedBorder]

        self.assertEqual("1px", border.width)
        self.assertEqual("2px", border_red.width)
        self.assertEqual("1px", border_dotted.width)
        self.assertEqual("solid", border.style)
        self.assertEqual("solid", border_red.style)
        self.assertEqual("dotted", border_dotted.style)
        self.assertEqual("black", border.color)
        self.assertEqual("red", border_red.color)
        self.assertEqual("black", border_dotted.color)

    def test_func(self) -> None:
        func = function(helpers.passthrough)
        self.assertEqual(((), {}), func.call(self.registry))

        func_simple = function(helpers.passthrough, 1, a="b")
        self.assertEqual(((1,), {"a": "b"}), func_simple.call(self.registry))

        self.registry.config.from_dict({"arg0": "val0", "value": "val_name"})
        func_config = function(helpers.passthrough, config("arg0"), name=config("value"))
        self.assertEqual((("val0",), {"name": "val_name"}), func_config.call(self.registry))

        func_nested = function(helpers.passthrough, function(helpers.nested, 2))
        self.assertEqual(((2,), {}), func_nested.call(self.registry))

        other = define(object)
        func_ref = function(helpers.passthrough, other=reference(other))
        self.assertEqual(((), {"other": self.registry[other]}), func_ref.call(self.registry))

        func_factory: _RegistryFunction[str] = function("create", reference(helpers.Factory), 1)
        self.assertEqual("1", func_factory.call(self.registry))

    def test_mock(self) -> None:
        """Test canonical usage of mock"""

        @bind(a="hello", b="world")
        class ClassToMock:
            def __init__(self, a, b):
                a.upper()
                self.a = a
                self.b = b

            def p(self):
                self.b.lower()

        mocked = mock(ClassToMock)
        mocked.a.upper.assert_called_once()
        mocked.b.upper.assert_not_called()
        mocked.b.lower.assert_not_called()
        mocked.p()
        mocked.b.lower.assert_called_once()

    def test_mock_with_define(self) -> None:
        """
        Test that mock works with metadata keys created
        through inject.define
        """

        class ClassToMock:
            def __init__(self, a, b):
                a.upper()
                self.a = a
                self.b = b

            def p(self):
                self.b.lower()

        my_class = define(ClassToMock, a="hi", b="bye")
        mocked = mock(my_class)

        mocked.a.upper.assert_called_once()
        mocked.b.upper.assert_not_called()

        mocked.p()
        mocked.b.lower.assert_called_once()

    def test_failed_mock_no_binding(self) -> None:
        """Test that mock fails when a class has no bindings available"""

        class ClassToMock:
            def __init__(self, a):
                print(a)

        my_class = define(ClassToMock)
        with self.assertRaises(TypeError):
            mock(my_class)

    def test_failed_mock_str_key(self) -> None:
        class MyClass:
            def __init__(self, a):
                self.a = a

        self.registry["a"] = MyClass("hi")
        with self.assertRaises(KeyError):
            mock("a")

    def test_mock_already_instantiated_class(self) -> None:
        class MyClass:
            def __init__(self, a):
                self.a = a

            def call_a(self):
                return self.a()

        definition = define(MyClass, a="hi")
        _ = self.registry[definition]
        mocked = mock(definition)
        mocked.call_a()
        mocked.a.assert_called_once()

    def test_mock_only_specified_bindings(self) -> None:
        """
        Test that default arguments are not mocked if bindings
        are not specified for those arguments
        """

        @bind(a="a")
        class MyClass:
            def __init__(self, a, b=None):
                self.a = a
                self.b = b

        mocked = mock(MyClass)
        assert isinstance(mocked.a, str)
        assert mocked.b is None

    def test_mock_multi_level_bind(self) -> None:
        """Test that a class with deferred bindings can be mocked"""

        @bind(a="a")
        class MyClass:
            def __init__(self, a, b=None):
                self.a = a
                self.b = b

            def call_a(self):
                self.a()

        @bind(c=reference(MyClass))
        class MyChildClass:
            def __init__(self, c):
                self.c = c

            def call_a(self):
                self.c.call_a()

        mocked = mock(MyChildClass)
        mocked.call_a()
        mocked.c.call_a.assert_called_once()

    def test_mock_multi_level_define(self) -> None:
        """
        Test that class with deferred bindings specified
        through inject.define can be mocked
        """

        class MyClass:
            def __init__(self, a, b=None):
                self.a = a
                self.b = b

            def call_a(self):
                self.a()

        class MyChildClass:
            def __init__(self, c):
                self.c = c

            def call_a(self):
                self.c.call_a()

        d0 = define(MyClass, a="a")
        d1 = define(MyChildClass, c=reference(d0))

        mocked = mock(d1)
        mocked.call_a()
        mocked.c.call_a.assert_called_once()

    def test_mock_inherited_binding(self) -> None:
        """Test that a class with inherited bindings can be mocked"""

        @bind(a="a", b="b")
        class MyClass:
            def __init__(self, a, b=None):
                self.a = a
                self.b = b

            def call_a(self):
                self.a()

        class MyChildClass(MyClass):
            def __init__(self, a, b):
                self.a = a
                self.b = b

            def call_a(self):
                self.a.upper()

        mocked = mock(MyChildClass)
        mocked.call_a()
        mocked.a.upper.assert_called_once()
        mocked.b.upper.assert_not_called()

    def test_autostart(self) -> None:
        self.registry.config.from_dict(
            {"registry": {"autostart": ["tests.test_registry_helpers.FakeWorker"]}}
        )

        self.registry.start()
        self.assertIsNotNone(getattr(helpers.FakeWorker, "instance", None))
        self.assertTrue(getattr(helpers.FakeWorker.instance, "_started", False))  # type: ignore
        self.assertFalse(getattr(helpers.FakeWorker.instance, "_closed", False))  # type: ignore

        self.registry.close()
        self.assertTrue(getattr(helpers.FakeWorker.instance, "_closed", False))  # type: ignore

    def test_self(self) -> None:
        func_logic = function(helpers.logic, self_tag)
        self.assertEqual(self.registry, func_logic.call(self.registry))

    def test_inherited_start_stop(self) -> None:
        class Base:
            def __init__(self):
                self.started: bool = False
                self.closed: bool = False

        def start(base: Base):
            base.started = True

        def close(base: Base):
            base.closed = True

        @bind(_start=start, _close=close)
        class Sub(Base):
            ...

        # Registry starts on initial lookup as part of the initiation process
        instance = self.registry[Sub]
        assert instance.started == True
        assert instance.closed == False
        # Close the registry
        self.registry.close()
        assert instance.started == True
        assert instance.closed == True

    def test_multiple_deferred_bindings(self) -> None:
        @bind()
        class Foo:
            def foo(self):
                return "foo"

        @bind()
        class Bar:
            def bar(self):
                return "bar"

        @bind(foo=reference(Foo), bar=reference(Bar))
        class MultipleBindings:
            def __init__(self, foo: Foo, bar: Bar):
                self.foo = foo
                self.bar = bar

        assert self.registry[MultipleBindings].foo.foo() == "foo"
        assert self.registry[MultipleBindings].bar.bar() == "bar"


# "Test"/check type hints.  These are not meant to be run by the unit test runner, but instead to
# be checked (and possibly fail if there is a bug) by the type checker - mypy.
def check_registry_interface_variance_resolvable() -> None:
    # pylint: disable=unsubscriptable-object
    subs: Sequence[Resolvable[_Sub]] = [_Sub(), _Sub(), _RegistryReference(_Sub)]
    # pylint: disable=unsubscriptable-object
    supers: Sequence[Resolvable[_Super]] = subs
    assert subs == supers


def check_registry_interface_variance_convenience_methods() -> None:
    # Test that variance is bound to the type (RegistryMetadata) and not the method.
    DefinedSub = define(_Sub)

    def check_covariance(_: RegistryMetadata[_Super]) -> None:
        ...

    check_covariance(DefinedSub)


def check_registry_interface_variance_reference() -> None:
    # Note: We do this in two steps as
    # super: _RegistryReference[_Super] = _RegistryReference(_Sub)
    # passes even in old code as the _RegistryReference.__init__() takes a
    # "RegistryKey[T]" which in this case is a "Type[T]" and "Type" is covariant.
    # We make things explicit here to ensure we are checking for _RegistryReference's covariance
    # and not involving inference too much.
    sub: _RegistryReference[_Sub] = _RegistryReference(_Sub)
    sup: _RegistryReference[_Super] = sub
    assert sup


def check_registry_interface_variance_config() -> None:
    sub: _RegistryConfig[_Sub] = _RegistryConfig("akey", default=_Sub())
    sup: _RegistryConfig[_Super] = sub
    assert sup


def check_registry_interface_variance_nested_config() -> None:
    sub: _RegistryNestedConfig[_Sub] = _RegistryNestedConfig("a.nested.key", default=_Sub())
    sup: _RegistryNestedConfig[_Super] = sub
    assert sup


if __name__ == "__main__":
    unittest.main()
