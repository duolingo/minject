from types import TracebackType
from typing import Any, Dict, Type, TypeVar

from typing_extensions import Protocol, Self, runtime_checkable

Arg = Any
Kwargs = Dict[str, Arg]

# MinimumMapping Key
K_contra = TypeVar("K_contra", contravariant=True)
# MinimumMapping Value
V_co = TypeVar("V_co", covariant=True)


@runtime_checkable
class _MinimalMappingProtocol(Protocol[K_contra, V_co]):
    """
    Defines the minimum methods needed for the dict-like objects acceptable to RegistryNestedConfig.
    """

    def __getitem__(self, key: K_contra) -> V_co:
        ...

    def __contains__(self, key: K_contra) -> bool:
        ...


class _AsyncContext(Protocol):
    """
    Protocol for any object that can be used as an async context manager.
    """

    async def __aenter__(self: Self) -> Self:
        ...

    async def __aexit__(
        self, exc_type: Type[BaseException], exc_value: BaseException, traceback: TracebackType
    ) -> None:
        ...
