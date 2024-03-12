from attr import field

from minject.inject import bind
from minject.inject_attrs import inject_define, inject_field
from minject.registry import Registry


def test_registry_instantiation() -> None:
    @inject_define
    class TestClass:
        a: str = inject_field(binding="hello")
        b: float = inject_field(binding=10.0)
        c: int = 100
        d: str = inject_field(binding="hello", default="world")
        e: bool = inject_field(binding=True, default=False)
        f: int = field(default=1000)
        g: int = inject_field(binding=1, default=2)

        def sum_nums(self) -> int:
            return self.c + int(self.b) + self.g + self.f

    registry = Registry()
    registry_instance = registry[TestClass]
    assert registry_instance.sum_nums() == 1111
    assert registry_instance.a == "hello"
    assert registry_instance.d == "hello"
    assert registry_instance.e == True


def test_bind_with_define() -> None:
    @bind(a=4)  # type: ignore
    @inject_define
    class TestClass:
        a: int
        b: int = inject_field(binding=100)

        def a_x_100(self) -> int:
            return self.a * self.b

    registry = Registry()
    registry_instance = registry[TestClass]
    assert registry_instance.a_x_100() == 400


def test_pass_args_to_attrs():
    a_kwarg_binding = "hello"

    @inject_define(define_kwargs={"eq": False})
    class TestClassNoEq:
        a: str = inject_field(binding=a_kwarg_binding)

    @inject_define(define_kwargs={"eq": True})
    class TestClassEq:
        a: str = inject_field(binding=a_kwarg_binding)

    registry = Registry()
    reg_no_eq = registry[TestClassNoEq]
    reg_eq = registry[TestClassEq]

    no_eq = TestClassNoEq(a=a_kwarg_binding)
    eq = TestClassEq(a=a_kwarg_binding)

    assert reg_no_eq != no_eq
    assert reg_eq == eq


def test_normal_instantiation() -> None:
    @inject_define
    class TestClass:
        a: str
        b: float = inject_field(binding=10.0)
        c: int = 100
        d: int = field(default=1000)
        f: int = inject_field(binding=1, default=2)

        def sum_nums(self) -> int:
            return self.c + int(self.b) + self.f + self.d

    normal_instance = TestClass(a="hi", b=10000)
    assert normal_instance.sum_nums() == 11102


def test_validator() -> None:
    # test validator works

    def less_than_10(self, attr, val):
        del self, attr
        if val >= 10:
            raise ValueError("val must be less than 10")

    @inject_define
    class TestClass:
        a: int = inject_field(binding=1, default=2, validator=less_than_10)

    try:
        TestClass(a=10)
        assert False
    except ValueError:
        assert True


def test_attr_defaults() -> None:
    """
    Test that default configuration is applied if
    define_kwargs is not passed to inject_define.
    """

    @inject_define
    class TestClassOne:
        ...

    @inject_define(define_kwargs={})
    class TestClassTwo:
        ...

    assert TestClassOne() != TestClassOne()
    assert TestClassTwo() == TestClassTwo()
