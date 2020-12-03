import abc
from typing import Generic, Union, Type, TypeVar  # pylint: disable=unused-import

import six

from .config import RegistryConfigWrapper  # pylint: disable=unused-import
from .metadata import RegistryMetadata

T = TypeVar("T")


RegistryKey = Union[Type[T], RegistryMetadata[T]]


class Resolver(six.with_metaclass(abc.ABCMeta, object)):
    """
    Interface capable of resolving keys and deferred values into instances.
    This interface primarily exists as a way to create a forward reference to Registry.
    """

    @abc.abstractmethod
    def resolve(self, key):
        # type: (RegistryKey[T]) -> T
        pass

    @abc.abstractproperty
    def config(self):
        # type: () -> RegistryConfigWrapper
        pass


class Deferred(six.with_metaclass(abc.ABCMeta, Generic[T])):
    """
    Deferred reference to a value which can be resolved with the help of a Registry instance.
    """

    @abc.abstractmethod
    def resolve(self, registry_impl):
        # type: (Resolver) -> T
        pass


Resolvable = Union[Deferred[T], T]


def resolve_value(registry_impl, value):
    # type: (Resolver, Resolvable[T]) -> T
    """
    Resolve a Resolvable value into a concrete value from the given registry.
    If value is an instance of Deferred, it will be resolved using the provided
    resolver, otherwise it is already a concrete value and will be returned as is.
    """
    if isinstance(value, Deferred):
        return value.resolve(registry_impl)
    else:
        return value