"""Metadata defines how a class should be initialized by the Registry."""

import inspect
import itertools
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Generic,
    Hashable,
    Optional,
    Sequence,
    Type,
    TypeVar,
)

from .model import DeferredAny, RegistryKey
from .types import Kwargs

if TYPE_CHECKING:
    from .registry import Registry

T = TypeVar("T")
T_co = TypeVar("T_co", covariant=True)

_INJECT_METADATA_ATTR = "_inject_meta"


def _get_meta(cls: Type[T], include_bases: bool = True) -> "Optional[RegistryMetadata[T]]":
    """
    Get the registry metadata from a class and possibly its base classes.
    Parameters:
        cls: the type for which to get metadata.
        include_bases: True to return any base class metadata, False to only check cls.
    Returns:
        Registry metadata describing the given cls if found, otherwise None
    """
    # load metadata from the class definition
    if include_bases:
        return getattr(cls, _INJECT_METADATA_ATTR, None)
    else:
        return cls.__dict__.get(_INJECT_METADATA_ATTR)


def _get_meta_from_key(key: "RegistryKey[T]") -> "RegistryMetadata[T]":
    """
    Given a RegistryKey, return the metadata associated with the key.
    A RegistryKey can have metadata associated with it in the following ways:

    - As a class attribute
    - As a class attribute on a base class
    - The key can be a type, in which case metadata is generated from the
      type without bindings.
    - The key itself can be RegistryMetadata

    String keys cannot have metadata associated with them. Passing a string key
    to this function raises a KeyError.
    """
    if isinstance(key, type):
        meta = _get_meta(key, include_bases=False)
        if meta is not None:
            return meta
        else:
            base = _get_meta(key, include_bases=True)
            if base is not None:
                meta = RegistryMetadata(key, bindings=dict(base.bindings))
            else:
                meta = RegistryMetadata(key)
            return meta
    elif isinstance(key, RegistryMetadata):
        return key
    else:
        raise KeyError(f"cannot get metadata from key: {key!r}")


def _gen_meta(cls: Type[T]) -> "RegistryMetadata[T]":
    """
    Get the registry metadata from a class, generating it if missing.
    If the provided class has base classes with metadata defined but not its own, the new metadata
    instance returned will inherit from the base class implementation.
    TODO: take into account multiple inheritance!!! (in _get_meta above too)
    Parameters:
        cls: the type for which to get metadata.
    Returns:
        Registry metadata describing the given cls if found, otherwise a new metadata instance.
    """
    # load metadata from the class definition
    meta: Optional[RegistryMetadata] = getattr(cls, _INJECT_METADATA_ATTR, None)
    if meta is None or _INJECT_METADATA_ATTR not in cls.__dict__:
        # meta does not exist or is from parent class
        if meta:
            # new metadata inheriting from the parent
            meta = RegistryMetadata(cls, bindings=dict(meta.bindings))
        else:
            meta = RegistryMetadata(cls)
        # store the metadata on the class definition
        setattr(cls, _INJECT_METADATA_ATTR, meta)
    return meta


class RegistryMetadata(Generic[T_co]):
    """Metadata for a registry key."""

    def __init__(
        self,
        cls: Type[T_co],
        close: Optional[Callable[[T_co], None]] = None,
        bindings: Optional[Kwargs] = None,
    ):
        self._cls = cls
        self._bindings = bindings or {}

        self._close = close
        self._interfaces = [cls for cls in inspect.getmro(cls) if cls is not object]

    @property
    def interfaces(self) -> Sequence[Type]:
        """Get the interfaces that this object provides."""
        return self._interfaces

    @property
    def key(self) -> Hashable:
        """The unique identifier used by this registry object.
        This is a combination of class and bindings.
        """
        return self._gen_key()

    def _gen_key(self):
        cls_and_bindings = (self._cls,) + tuple(self._bindings.items())
        return cls_and_bindings

    @property
    def bindings(self) -> Kwargs:
        """Get the 'bindings' (init args) for this registry object."""
        return self._bindings

    def update_bindings(self, **bindings: DeferredAny) -> None:
        """Upate the 'bindings' (init args) for this registry object.
        NOTE: DO NOT change the bindings after this metadata has been
        added to the registry, it will cause undefined behavior.
        """
        # TODO: 'lock' the bindings once added to the registry to make above note unnecessary
        self._bindings.update(bindings)

    def _new_object(self) -> T_co:
        return self._cls.__new__(self._cls)

    # Because of the class design for RegistryMetadata and RegistryWrapper, where the wrapper
    # "owns" the object (and a reference to the metadata), but the metadata contains the logic
    # for creating and initializing the object we have a covariant type in a few of our methods.
    # These methods should not be used outside of the Registry and RegistryWrapper classes as they
    # compromise the type safety of this RegistryMetadata class.
    # TODO: Refactor these methods to belong to RegistryWrapper which has a reference to both
    # the metadata and the object throughout its creation->initialization phase
    def _init_object(self, obj: T_co, registry_impl: "Registry") -> None:  # type: ignore[misc]
        init_kwargs = {}
        for name_, value in self._bindings.items():
            init_kwargs[name_] = registry_impl._resolve(value)

        self._cls.__init__(obj, **init_kwargs)

    def _close_object(self, obj: T_co) -> None:  # type: ignore[misc]
        if self._close:
            self._close(obj)

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, RegistryMetadata):
            return self.key == other.key
        else:
            return NotImplemented

    def __hash__(self) -> int:
        return hash(self.key)

    def __str__(self) -> str:
        return f"{self.key}"

    def __repr__(self) -> str:
        return f"<RegistryMetadata {self.key}>"
