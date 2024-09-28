

from typing import Type
import pytest
from minject.registry import Registry
from minject.inject import bind, reference, async_context

from types import TracebackType

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
    
    async def __aexit__(self, exc_type : Type[BaseException], exc_value : BaseException, traceback : TracebackType) -> None:
        del exc_type, exc_value, traceback
        self.in_context = False
        pass

@async_context
class MyDependencyAsync:
    def __init__(self) -> None:
        self.in_context = False
    
    async def __aenter__(self) -> "MyDependencyAsync":
        self.in_context = True
        return self
    
    async def __aexit__(self, exc_type : Type[BaseException], exc_value : BaseException, traceback : TracebackType) -> None:
        del exc_type, exc_value, traceback
        self.in_context = False
        pass

@async_context
@bind(text=TEXT)
@bind(dep_async=reference(MyDependencyAsync))
@bind(dep_not_specified=reference(MyDependencyNotSpecifiedAsync))
class MyApi:
    def __init__(self, text : str, dep_async : MyDependencyAsync, dep_not_specified : MyDependencyNotSpecifiedAsync) -> None:
        self.text = text
        self.in_context = False
        self.dep_async = dep_async
        self.dep_not_specified = dep_not_specified

    async def __aenter__(self) -> "MyApi":
        self.in_context = True
        return self
    
    async def __aexit__(self, exc_type : Type[BaseException], exc_value : BaseException, traceback : TracebackType) -> None:
        del exc_type, exc_value, traceback
        self.in_context = False
        pass

async def test_async_registry(registry : Registry) -> None:
    async with registry as r:
        my_api = r[MyApi]
        assert my_api.text == TEXT
        assert my_api.in_context == True
        assert my_api.dep_async.in_context == True
        assert my_api.dep_not_specified.in_context == False

    assert my_api.in_context == False
    assert my_api.dep_async.in_context == False
    assert my_api.dep_not_specified.in_context == False



