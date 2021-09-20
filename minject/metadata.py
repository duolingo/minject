"""Metadata defines how a class should be initialized by the Registry."""

import inspect
import itertools
from typing import Dict  # pylint: disable=unused-import
from typing import Any, Callable, Generic, List, Optional, Type, TypeVar

import six

T = TypeVar("T")

_INJECT_METADATA_ATTR = "_inject_meta"


def _get_meta(cls, include_bases=True):
    # type: (type, bool) -> Optional[RegistryMetadata]
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


def _gen_meta(cls):
    # type: (type) -> RegistryMetadata
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
    meta = getattr(cls, _INJECT_METADATA_ATTR, None)
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


class RegistryMetadata(Generic[T]):
    """Metadata for a registry key."""

    def __init__(
        self,
        cls,  # type: Type[T]
        name=None,  # type: Optional[str]  # pylint: disable=redefined-outer-name
        start=None,  # type: Optional[Callable[[T], None]]
        close=None,  # type: Optional[Callable[[T], None]]
        bindings=None,  # type: Optional[Dict[str, Any]]
        key=None,  # type: Optional[Any]
    ):
        self._cls = cls
        self._bindings = bindings or {}

        # TODO(1.0): deprecated, not used
        self._name = name
        self._start = start
        self._close = close
        self._interfaces = [cls for cls in inspect.getmro(cls) if cls is not object]

        self._key = key

    @property
    def name(self):  # type: () -> Optional[str]
        """Get the name this object is stored as in the registry."""
        return self._name

    @name.setter
    def name(self, name_):  # type: (str) -> None
        self._name = name_

    @property
    def interfaces(self):  # type: () -> List[type]
        """Get the interfaces that this object provides."""
        return self._interfaces

    @property
    def key(self):  # type: () -> Any
        """The unique identifier used by this registry object.
        By default this is a combination of class and bindings."""
        if self._key is None:
            self._key = self._gen_key()
        return self._key

    def _gen_key(self):
        return tuple(
            itertools.chain(
                (self._cls, self._name), (item for item in six.iteritems(self._bindings))
            )
        )

    @property
    def bindings(self):  # type: () -> dict
        """Get the 'bindings' (init args) for this registry object."""
        return self._bindings

    def update_bindings(self, **bindings):  # type: (Any) -> None
        """Upate the 'bindings' (init args) for this registry object.
        NOTE: DO NOT change the bindings after this metadata has been
        added to the registry, it will cause undefined behavior."""
        # TODO: 'lock' the bindings once added to the registry to make above note unnecessary
        self._bindings.update(bindings)

    def _new_object(self):
        return self._cls.__new__(self._cls)

    def _init_object(self, obj, registry_impl):
        init_kwargs = {}
        for name_, value in six.iteritems(self._bindings):
            init_kwargs[name_] = registry_impl._resolve(value)

        config_ = registry_impl.config.get_init_kwargs(self)
        if config_:
            for name_, value in six.iteritems(config_):
                init_kwargs[name_] = value

        self._cls.__init__(obj, **init_kwargs)

    def _start_object(self, obj):
        if self._start:
            self._start(obj)

    def _close_object(self, obj):
        if self._close:
            self._close(obj)

    def __eq__(self, other):
        if isinstance(other, RegistryMetadata):
            return self.key == other.key
        else:
            return NotImplemented

    def __hash__(self):
        return hash(self.key)

    def __str__(self):
        return "{} {}({})".format(
            repr(self._name) if self._name else "(unnamed)",
            self._cls.__name__,
            ", ".join(["{}={}".format(*item) for item in six.iteritems(self._bindings)]),
        )

    def __repr__(self):
        return "<RegistryMetadata {} {}({})>".format(
            repr(self._name) if self._name else "(unnamed)", self._cls.__name__, self._bindings
        )
