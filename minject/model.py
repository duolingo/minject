import abc
from typing import Type  # pylint: disable=unused-import
from typing import TYPE_CHECKING, Any, Generic, TypeVar, Union

from typing_extensions import TypeAlias

from .config import RegistryConfigWrapper

T = TypeVar("T")


if TYPE_CHECKING:
    from .metadata import RegistryMetadata

RegistryKey: TypeAlias = "Union[str, Type[T], RegistryMetadata[T]]"


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


class Deferred(abc.ABC, Generic[T]):
    """
    Deferred reference to a value which can be resolved with the help of a Registry instance.
    """

    @abc.abstractmethod
    def resolve(self, registry_impl: Resolver) -> T:
        ...


Resolvable = Union[Deferred[T], T]
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
