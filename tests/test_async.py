from types import TracebackType
from typing import Dict, Type

import pytest

from minject.inject import async_context, bind, config, define, nested_config, reference
from minject.registry import AUTO_OR_NONE, Registry

TEXT = "we love tests"


@pytest.fixture
def registry() -> Registry:
    config_dict: Dict[str, str] = {"a": {"b": "c"}, 1: 2}
    r = Registry(config=config_dict)
    return r


class MyDependencyNotSpecifiedAsync:
    def __init__(self) -> None:
        self.in_context = False

    async def __aenter__(self) -> "MyDependencyNotSpecifiedAsync":
        self.in_context = True
        return self

    async def __aexit__(
        self, exc_type: Type[BaseException], exc_value: BaseException, traceback: TracebackType
    ) -> None:
        del exc_type, exc_value, traceback
        self.in_context = False


@async_context
class MyDependencyAsync:
    def __init__(self) -> None:
        self.in_context = False

    async def __aenter__(self) -> "MyDependencyAsync":
        self.in_context = True
        return self

    async def __aexit__(
        self, exc_type: Type[BaseException], exc_value: BaseException, traceback: TracebackType
    ) -> None:
        del exc_type, exc_value, traceback
        self.in_context = False


@async_context
class MyAsyncAPIContextCounter:
    def __init__(self) -> None:
        self.in_context = False
        self.entered_context_counter = 0
        self.exited_context_counter = 0

    async def __aenter__(self) -> "MyAsyncAPIContextCounter":
        self.in_context = True
        self.entered_context_counter += 1
        return self

    async def __aexit__(
        self, exc_type: Type[BaseException], exc_value: BaseException, traceback: TracebackType
    ) -> None:
        del exc_type, exc_value, traceback
        self.exited_context_counter += 1
        self.in_context = False


@bind(dep_async=reference(MyDependencyAsync))
class MySyncClassWithAsyncDependency:
    def __init__(self, dep_async: MyDependencyAsync) -> None:
        self.dep_async = dep_async


@bind(_close=lambda self: self.close())
class MySyncClassWithCloseMethod:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


@async_context
@bind(sync_close_dep=reference(MySyncClassWithCloseMethod))
class MyAsyncClassWithSyncCloseDependency:
    def __init__(
        self, sync_close_dep: "MySyncClassWithCloseMethod", will_throw: bool = False
    ) -> None:
        self.sync_close_dep = sync_close_dep
        self.entered = False
        self.will_throw = will_throw

    async def __aenter__(self) -> "MyAsyncClassWithSyncCloseDependency":
        self.entered = True
        return self

    async def __aexit__(
        self, exc_type: Type[BaseException], exc_value: BaseException, traceback: TracebackType
    ) -> None:
        del exc_type, exc_value, traceback
        self.entered = False
        if self.will_throw:
            raise ValueError("This is a test error")


@async_context
@bind(text=TEXT)
@bind(dep_async=reference(MyDependencyAsync))
@bind(dep_not_specified=reference(MyDependencyNotSpecifiedAsync))
@bind(dep_context_counter=reference(MyAsyncAPIContextCounter))
class MyAsyncApi:
    def __init__(
        self,
        text: str,
        dep_async: MyDependencyAsync,
        dep_not_specified: MyDependencyNotSpecifiedAsync,
        dep_context_counter: MyAsyncAPIContextCounter,
    ) -> None:
        self.text = text
        self.in_context = False
        self.dep_async = dep_async
        self.dep_not_specified = dep_not_specified
        self.dep_context_counter = dep_context_counter

    async def __aenter__(self) -> "MyAsyncApi":
        self.in_context = True
        return self

    async def __aexit__(
        self, exc_type: Type[BaseException], exc_value: BaseException, traceback: TracebackType
    ) -> None:
        del exc_type, exc_value, traceback
        self.in_context = False


MY_ASYNC_API_DEFINE = define(
    MyAsyncApi,
    text=TEXT,
    dep_async=reference(MyDependencyAsync),
    dep_not_specified=reference(MyDependencyNotSpecifiedAsync),
    dep_context_counter=reference(MyAsyncAPIContextCounter),
)


@async_context
@bind(nested=nested_config("a.b"))
@bind(flat=config(1))
class MyAsyncApiWithConfig:
    def __init__(self, nested: str, flat: int) -> None:
        self.nested = nested
        self.flat = flat

    async def __aenter__(self) -> "MyAsyncApiWithConfig":
        return self

    async def __aexit__(
        self, exc_type: Type[BaseException], exc_value: BaseException, traceback: TracebackType
    ) -> None:
        pass


@async_context
class BadContextManager:
    def __init__(self) -> None:
        pass

    async def __aenter__(self) -> 1:
        return 1

    async def __aexit__(
        self, exc_type: Type[BaseException], exc_value: BaseException, traceback: TracebackType
    ):
        pass


async def test_async_registry_simple(registry: Registry) -> None:
    async with registry as r:
        my_api = await r.aget(MyDependencyAsync)
        assert my_api.in_context == True

    assert my_api.in_context == False


async def test_async_registry_recursive(registry: Registry) -> None:
    async with registry as r:
        my_api = await r.aget(MyAsyncApi)
        assert my_api.text == TEXT
        assert my_api.in_context == True
        assert my_api.dep_async.in_context == True
        assert my_api.dep_not_specified.in_context == False
        assert my_api.dep_context_counter.in_context == True
        assert my_api.dep_context_counter.entered_context_counter == 1

    assert my_api.in_context == False
    assert my_api.dep_async.in_context == False
    assert my_api.dep_not_specified.in_context == False
    assert my_api.dep_context_counter.in_context == False
    assert my_api.dep_context_counter.exited_context_counter == 1


async def test_multiple_instantiation_child(registry: Registry) -> None:
    my_api: MyAsyncApi
    async with registry as r:
        my_api = await r.aget(MyAsyncApi)
        my_api_2 = await r.aget(MyAsyncApi)
        my_api_3 = await r.aget(MyAsyncApi)
        assert my_api is my_api_2 is my_api_3

        assert my_api.dep_context_counter.entered_context_counter == 1

    assert my_api.dep_context_counter.exited_context_counter == 1


async def test_multiple_instantiation_top_level(registry: Registry) -> None:
    my_counter: MyAsyncAPIContextCounter
    async with registry as r:
        my_counter = await r.aget(MyAsyncAPIContextCounter)
        my_api_2 = await r.aget(MyAsyncAPIContextCounter)
        my_api_3 = await r.aget(MyAsyncAPIContextCounter)
        assert my_counter is my_api_2 is my_api_3
        assert my_counter.entered_context_counter == 1
    assert my_counter.exited_context_counter == 1


async def test_multiple_instantiation_mixed(registry: Registry) -> None:
    my_counter: MyAsyncAPIContextCounter
    async with registry as r:
        my_counter = await r.aget(MyAsyncAPIContextCounter)
        assert my_counter.entered_context_counter == 1
        await r.aget(MyAsyncApi)
        assert my_counter.entered_context_counter == 1
    assert my_counter.exited_context_counter == 1


async def test_async_context_outside_context_manager(registry: Registry) -> None:
    with pytest.raises(AssertionError):
        # attempting to instantiate a class
        # marked with @async_context without
        # being in an async context should
        # raise an error
        _ = await registry.aget(MyAsyncApi)


async def test_try_instantiate_async_class_with_sync_api(registry: Registry) -> None:
    with pytest.raises(AssertionError):
        # attempting to instantiate a class
        # marked with @async_context using sync API
        # should raise an error
        _ = registry[MyDependencyAsync]

    with pytest.raises(AssertionError):
        # still throws an error even when registry context
        # has been entered
        async with registry as r:
            _ = r[MyAsyncApi]


async def test_context_manager_aenter_must_return_self(registry: Registry) -> None:
    """
    Async context manager must return self from aenter method,
    throw value error otherwise.
    """
    async with registry as r:
        with pytest.raises(ValueError):
            _ = await r.aget(BadContextManager)


async def test_config_in_async(registry: Registry) -> None:
    async with registry as r:
        r = await r.aget(MyAsyncApiWithConfig)
        assert r.nested == "c"
        assert r.flat == 2


async def test_entering_already_entered_registry_throws(registry: Registry) -> None:
    async with registry as r:
        with pytest.raises(AssertionError):
            async with r:
                pass


async def test_define(registry: Registry) -> None:
    async with registry as r:
        my_api = await r.aget(MY_ASYNC_API_DEFINE)
        assert my_api.text == TEXT
        assert my_api.in_context == True
        assert my_api.dep_async.in_context == True
        assert my_api.dep_not_specified.in_context == False
        assert my_api.dep_context_counter.in_context == True
        assert my_api.dep_context_counter.entered_context_counter == 1

    assert my_api.in_context == False
    assert my_api.dep_async.in_context == False
    assert my_api.dep_not_specified.in_context == False
    assert my_api.dep_context_counter.in_context == False
    assert my_api.dep_context_counter.exited_context_counter == 1


def test_get_item_sync_class_async_dependency_throws(registry: Registry) -> None:
    with pytest.raises(AssertionError):
        _ = registry[MySyncClassWithAsyncDependency]


def test_get_sync_class_async_dependency_throws(registry: Registry) -> None:
    with pytest.raises(AssertionError):
        _ = registry.get(MySyncClassWithAsyncDependency, AUTO_OR_NONE)


async def test_exit_logic_success(registry: Registry) -> None:
    async with registry as r:
        my_cls = await r.aget(MyAsyncClassWithSyncCloseDependency)
        assert my_cls.entered == True
        assert my_cls.sync_close_dep.closed == False

    assert my_cls.entered == False
    assert my_cls.sync_close_dep.closed == True


async def test_exit_logic_failure(registry: Registry) -> None:
    with pytest.raises(ValueError):
        async with registry as r:
            bindings = define(
                MyAsyncClassWithSyncCloseDependency,
                sync_close_dep=reference(MySyncClassWithCloseMethod),
                will_throw=True,
            )
            my_cls = await r.aget(bindings)
            assert my_cls.entered == True
            assert my_cls.sync_close_dep.closed == False

    assert my_cls.entered == False
    assert my_cls.sync_close_dep.closed == True

