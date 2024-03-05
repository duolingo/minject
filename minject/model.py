import abc
from typing import (  # pylint: disable=unused-import
    TYPE_CHECKING,
    Any,
    Callable,
    Generic,
    Type,
    TypeVar,
    Union,
)

from typing_extensions import TypeAlias

from .config import RegistryConfigWrapper
from .types import Arg

T = TypeVar("T")
T_co = TypeVar("T_co", covariant=True)


if TYPE_CHECKING:
    from .metadata import RegistryMetadata

RegistryKey: TypeAlias = "Union[str, Type[T_co], RegistryMetadata[T_co]]"


class Resolver(abc.ABC):
    """
    Interface capable of resolving keys and deferred values into instances.
    This interface primarily exists as a way to create a forward reference to Registry.
    """

    @abc.abstractmethod
    def resolve(self, key: "RegistryKey[T]") -> T:
        ...

    @property
    @abc.abstractmethod
    def config(self) -> RegistryConfigWrapper:
        ...


MockingFunction: TypeAlias = Callable[[Arg], Any]


class Deferred(abc.ABC, Generic[T_co]):
    """
    Deferred reference to a value which can be resolved with the help of a Registry instance.
    """

    @abc.abstractmethod
    def resolve(self, registry_impl: Resolver) -> T_co:
        ...


Resolvable = Union[Deferred[T_co], T_co]
# Union of Deferred and Any is just Any, but want to call out that a Deffered is quite common
# and has special handling by the registry.
DeferredAny: TypeAlias = Union[Deferred, Any]


def resolve_value(registry_impl: Resolver, value: Resolvable[T]) -> T:
    """
    Resolve a Resolvable value into a concrete value from the given registry.
    If value is an instance of Deferred, it will be resolved using the provided
    resolver, otherwise it is already a concrete value and will be returned as is.
    """
    if isinstance(value, Deferred):
        return value.resolve(registry_impl)
    else:
        return value
