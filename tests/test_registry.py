import unittest

import tests.util.test_registry_helpers as helpers
from duolingo_base.util import registry


class RegistryTestCase(unittest.TestCase):
    def setUp(self):
        self.registry = registry.initialize()

    def test_by_name(self):
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

    def test_by_definition(self):
        self.assertNotIn(helpers.TestType, self.registry)
        self.assertIsNone(self.registry.get(helpers.TestType))

        test_obj = self.registry[helpers.TestType]
        self.assertIsInstance(test_obj, helpers.TestType)
        self.assertIs(test_obj, self.registry.get(helpers.TestType))

    def test_bindings(self):
        self.registry["name"] = "my_name"

        self.assertNotIn(helpers.Named, self.registry)

        named_obj = self.registry[helpers.Named]
        self.assertIsInstance(named_obj, helpers.Named)

        self.assertIs(named_obj, self.registry.get(helpers.Named))

        self.assertEqual("my_name", named_obj.name)

    def test_inheritance(self):
        bar = self.registry[helpers.Bar]

        self.assertIs(bar, self.registry[helpers.Bar])
        self.assertIs(bar, self.registry[helpers.Foo])
        self.assertIsNone(self.registry.get(object))

    def test_different_bindings(self):
        TaggerA = registry.define(helpers.Tagger, tag="a")
        TaggerB = registry.define(helpers.Tagger, tag="b")
        TaggerNone = registry.define(helpers.Tagger)
        TaggerAref = registry.define(helpers.Tagger, tag=registry.reference("a"))

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

    def test_nested_bind(self):
        outer = self.registry[helpers.Outer]

        self.assertEqual("outer", outer.name)
        self.assertIsNotNone(outer.inner)
        self.assertEqual("inner", outer.inner.name)

        self.assertIs(outer, self.registry[helpers.Outer])
        self.assertIs(outer.inner, self.registry[helpers.Inner])

    def test_bind_inherit(self):
        IndexResource = registry.define(helpers.AbstractResource, path="/index.html")
        index = self.registry[IndexResource]

        self.assertEqual("/index.html", index.path)
        self.assertIsNotNone(index.server)
        self.assertEqual("http://localhost", index.server.url)
        self.assertIs(helpers.AbstractResource, index.__class__)
        self.assertIs(helpers.Server, index.server.__class__)

        AboutResource = registry.define(helpers.AbstractResource, path="/about.html")
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

        UndefResource = registry.define(helpers.AbstractResource)
        with self.assertRaises(TypeError):
            self.registry[UndefResource]  # pylint: disable=pointless-statement

        search = self.registry[helpers.SearchResource]

        self.assertEqual("/search.html", search.path)
        self.assertIsNotNone(search.server)
        self.assertEqual("http://localhost", search.server.url)
        self.assertIsNot(index, search)
        self.assertIs(index.server, search.server)

        DuolingoResource = registry.define(
            helpers.AbstractResource,
            path="/index.html",
            server=registry.reference(helpers.Server, url="http://duolingo.com"),
        )
        duo = self.registry[DuolingoResource]

        self.assertEqual("/index.html", duo.path)
        self.assertIsNotNone(duo.server)
        self.assertEqual("http://duolingo.com", duo.server.url)
        self.assertIsNot(index, duo)
        self.assertIsNot(index.server, duo.server)

    def test_nonbound_abstract(self):
        client = self.registry[helpers.MyApiClient]

        self.assertEqual("http://localhost/myapi", client.get())

    def test_config(self):
        RedBorder = registry.define(helpers.Border, color="red")
        RedBorder.name = "border_red"

        DottedBorder = registry.define(helpers.Border)
        DottedBorder.name = "border_dotted"

        self.registry.config.from_dict(
            {
                "registry": {
                    "by_class": {"tests.util.test_registry_helpers.Border": {"style": "solid"}},
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

    def test_func(self):
        func = registry.function(helpers.passthrough)
        self.assertEqual(((), {}), func.call(self.registry))

        func_simple = registry.function(helpers.passthrough, 1, a="b")
        self.assertEqual(((1,), {"a": "b"}), func_simple.call(self.registry))

        self.registry.config.from_dict({"arg0": "val0", "value": "val_name"})
        func_config = registry.function(
            helpers.passthrough, registry.config("arg0"), name=registry.config("value")
        )
        self.assertEqual((("val0",), {"name": "val_name"}), func_config.call(self.registry))

        func_nested = registry.function(helpers.passthrough, registry.function(helpers.nested, 2))
        self.assertEqual(((2,), {}), func_nested.call(self.registry))

        other = registry.define(object)
        func_ref = registry.function(helpers.passthrough, other=registry.reference(other))
        self.assertEqual(((), {"other": self.registry[other]}), func_ref.call(self.registry))

        func_factory = registry.function("create", registry.reference(helpers.Factory), 1)
        self.assertEqual("1", func_factory.call(self.registry))

    def test_autostart(self):
        self.registry.config.from_dict(
            {"registry": {"autostart": ["tests.util.test_registry_helpers.FakeWorker"]}}
        )

        self.registry.start()
        self.assertIsNotNone(getattr(helpers.FakeWorker, "instance", None))
        self.assertTrue(getattr(helpers.FakeWorker.instance, "_started", False))
        self.assertFalse(getattr(helpers.FakeWorker.instance, "_closed", False))

        self.registry.close()
        self.assertTrue(getattr(helpers.FakeWorker.instance, "_closed", False))

    def test_self(self):
        func_logic = registry.function(helpers.logic, registry.self_tag)
        self.assertEqual(self.registry, func_logic.call(self.registry))

    def test_inherited_start_stop(self):
        class Base:
            def __init__(self):
                self.started: bool = False
                self.closed: bool = False

        def start(base: Base):
            base.started = True

        def close(base: Base):
            base.closed = True

        @registry.bind(_start=start, _close=close)
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

    def test_multiple_deferred_bindings(self):
        @registry.bind()
        class Foo:
            def foo(self):
                return "foo"

        @registry.bind()
        class Bar:
            def bar(self):
                return "bar"

        @registry.bind(foo=registry.reference(Foo), bar=registry.reference(Bar))
        class MultipleBindings:
            def __init__(self, foo: Foo, bar: Bar):
                self.foo = foo
                self.bar = bar

        assert self.registry[MultipleBindings].foo.foo() == "foo"
        assert self.registry[MultipleBindings].bar.bar() == "bar"


if __name__ == "__main__":
    unittest.main()
