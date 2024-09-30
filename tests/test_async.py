from types import TracebackType
from typing import Type

import pytest

from minject.inject import async_context, bind, reference
from minject.registry import Registry, RegistryAPIError

TEXT = "we love tests"


@pytest.fixture
def registry() -> Registry:
    return Registry()


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


async def test_async_context_outside_context_manager(registry: Registry) -> None:
    with pytest.raises(RegistryAPIError):
        # attempting to instantiate a class
        # marked with @async_context without
        # being in an async context should
        # raise an error
        _ = await registry.aget(MyAsyncApi)


async def test_try_instantiate_async_class_with_sync_api(registry: Registry) -> None:
    with pytest.raises(RegistryAPIError):
        # attempting to instantiate a class
        # marked with @async_context using sync API
        # should raise an error
        _ = registry[MyDependencyAsync]

    with pytest.raises(RegistryAPIError):
        # still throws an error even when registry context
        # has been entered
        async with registry as r:
            _ = r[MyAsyncApi]