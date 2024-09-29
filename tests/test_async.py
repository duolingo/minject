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
@bind(text=TEXT)
@bind(dep_async=reference(MyDependencyAsync))
@bind(dep_not_specified=reference(MyDependencyNotSpecifiedAsync))
class MyAsyncApi:
    def __init__(
        self,
        text: str,
        dep_async: MyDependencyAsync,
        dep_not_specified: MyDependencyNotSpecifiedAsync,
    ) -> None:
        self.text = text
        self.in_context = False
        self.dep_async = dep_async
        self.dep_not_specified = dep_not_specified

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

    assert my_api.in_context == False
    assert my_api.dep_async.in_context == False
    assert my_api.dep_not_specified.in_context == False


async def test_multiple_instantiation(registry: Registry) -> None:
    async with registry as r:
        my_api = await r.aget(MyAsyncApi)
        my_api_2 = await r.aget(MyAsyncApi)
        my_api_3 = await r.aget(MyAsyncApi)
        assert my_api is my_api_2 is my_api_3


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
