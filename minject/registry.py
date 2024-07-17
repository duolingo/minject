"""The Registry itself is a runtime collection of initialized classes."""
import functools
import logging
from threading import RLock
from typing import Callable, Dict, Generic, Iterable, List, Optional, TypeVar, Union, cast

from typing_extensions import Concatenate, ParamSpec

from .config import RegistryConfigWrapper, RegistryInitConfig
from .metadata import RegistryMetadata, _get_meta, _get_meta_from_key
from .model import RegistryKey, Resolvable, Resolver, resolve_value

LOG = logging.getLogger(__name__)

T = TypeVar("T")
R = TypeVar("R")
P = ParamSpec("P")


class _AutoOrNone:
    def __nonzero__(self):
        return False

    def __bool__(self):
        return False


AUTO_OR_NONE = _AutoOrNone()


def initialize(config: Optional[RegistryInitConfig] = None) -> "Registry":
    """Initialize a new registry instance."""
    LOG.debug("initializing a new registry instance")
    return Registry(config)


def _unwrap(wrapper: Optional["RegistryWrapper[T]"]) -> Optional[T]:
    return wrapper.obj if wrapper else None


class RegistryWrapper(Generic[T]):
    """Simple wrapper around registered objects for tracking."""

    def __init__(self, obj: T, _meta: Optional[RegistryMetadata[T]] = None) -> None:
        self.obj = obj
        self._meta = _meta

    def close(self) -> None:
        if not getattr(self, "_closed", False) and self._meta:
            self._meta._close_object(self.obj)
        self._closed = True


def _synchronized(
    func: Callable[Concatenate["Registry", P], R]
) -> Callable[Concatenate["Registry", P], R]:
    """Decorator to synchronize method access with a reentrant lock."""

    @functools.wraps(func)
    def wrapper(self: "Registry", *args: P.args, **kwargs: P.kwargs) -> R:
        with self._lock:
            return func(self, *args, **kwargs)

    return wrapper


class Registry(Resolver):
    """Tracks and manages registered object instances."""

    def __init__(self, config: Optional[RegistryInitConfig] = None):
        self._objects: List[RegistryWrapper] = []
        self._by_meta: Dict[RegistryMetadata, RegistryWrapper] = {}
        self._by_name: Dict[str, RegistryWrapper] = {}
        self._by_iface: Dict[type, List[RegistryWrapper]] = {}
        self._config = RegistryConfigWrapper()

        self._lock = RLock()

        if config is not None:
            self._config._from_dict(config)

    @property
    def config(self) -> RegistryConfigWrapper:
        return self._config

    def resolve(self, key: "RegistryKey[T]") -> T:
        return self[key]

    def _resolve(self, value: Resolvable[T]) -> T:
        return resolve_value(self, value)

    @_synchronized
    def close(self) -> None:
        """Close all objects contained in the registry."""
        for wrapper in list(reversed(self._objects)):
            if wrapper._meta is not None:
                # call the object's close method, if defined
                wrapper.close()

    @_synchronized
    def register(
        self, obj: T, name: Optional[str] = None, interfaces: Optional[Iterable[type]] = None
    ) -> None:
        """Register a new object for discovery.

        Parameters:
            obj: the object to register.
            name: optional name to reference the object by.
            interfaces: optional interfaces this object provides.
        """
        LOG.debug("registering %s (name=%s, interfaces=%s)", obj, name, interfaces)

        wrapper = RegistryWrapper(obj)

        # add to our list of all objects
        self._objects.append(wrapper)

        # index by name if provided
        if name is not None:
            self._by_name[name] = wrapper

        # index by implemented interfaces if provided
        if interfaces is not None:
            for iface in interfaces:
                obj_list = self._by_iface.setdefault(iface, [])
                obj_list.append(wrapper)

    @_synchronized
    def _set_by_metadata(
        self, meta: RegistryMetadata[T], obj: T, _global: bool = True
    ) -> RegistryWrapper[T]:
        wrapper = RegistryWrapper(obj, meta)

        if _global:
            self._objects.append(wrapper)

        self._by_meta[meta] = wrapper
        if meta.interfaces:
            for iface in meta.interfaces:
                obj_list = self._by_iface.setdefault(iface, [])
                obj_list.append(wrapper)

        return wrapper

    @_synchronized
    def _remove_by_metadata(
        self, meta: RegistryMetadata[T], wrapper: RegistryWrapper[T], _global: bool = True
    ) -> None:
        if _global:
            self._objects.remove(wrapper)

        del self._by_meta[meta]
        if meta.interfaces:
            for iface in meta.interfaces:
                obj_list = self._by_iface.get(iface)
                if obj_list:
                    obj_list.remove(wrapper)

    @_synchronized
    def _register_by_metadata(self, meta: RegistryMetadata[T]) -> RegistryWrapper[T]:
        LOG.debug("registering %s", meta)

        # allocate the object (but don't initialize yet)
        obj = meta._new_object()

        # add to the registry (done before init in case of circular reference)
        wrapper = self._set_by_metadata(meta, obj, _global=False)

        success = False
        try:
            # initialize the object
            meta._init_object(obj, self)
            # add to our list of all objects (this MUST happen after init so
            # any references come earlier in sequence and are destroyed first)
            self._objects.append(wrapper)
            success = True
        finally:
            if not success:
                self._remove_by_metadata(meta, wrapper, _global=False)

        return wrapper

    @_synchronized
    def _get_by_metadata(
        self, meta: RegistryMetadata[T], default: Optional[Union[T, _AutoOrNone]] = AUTO_OR_NONE
    ) -> Optional[RegistryWrapper[T]]:
        """
        Get a registered object by metadata.
        Parameters:
            meta: the metadata which refers to the object.
            default: return value if meta has not been registered.
                Use AUTO_OR_NONE to create the object when missing.
        """
        if meta in self._by_meta:
            return self._by_meta[meta]

        if default is AUTO_OR_NONE:
            return self._register_by_metadata(meta)
        elif default is not None:
            return RegistryWrapper(cast(T, default))
        else:
            return None

    @_synchronized
    def __len__(self) -> int:
        return len(self._objects)

    def __contains__(self, key) -> bool:
        """Check if an object is contained in the registry.
        Note that this method returns True if the object has already been
        registered. It is possible that the key provides enough information
        to register the object automatically, in this scenario this method
        will return False.
        Parameters:
            key: a string name, type, or RegistryDefinition that will be used
                to find the object.
        Returns:
            True if the object is registered, false otherwise.
        """
        if isinstance(key, str):
            return key in self._by_name
        elif isinstance(key, type):
            return bool(self._by_iface.get(key))
        elif isinstance(key, RegistryMetadata):
            return bool(self._get_by_metadata(key, False))
        else:
            raise KeyError(f"invalid key for Registry: {key!r}")

    @_synchronized
    def get(
        self, key: "RegistryKey[T]", default: Optional[Union[T, _AutoOrNone]] = None
    ) -> Optional[T]:
        """Get an object from the registry by a key.

        Parameters:
            key: a string, type, or RegistryDefinition that will be used
                to find (or construct) the desired object.
            default: the value to return if the object is not found.
                if default is registry.AUTO_OR_NONE then the registry will
                attempt to register the object (if object has metadata).
        Returns:
            The requested object or default if not found.
        """
        if key == object:
            return None  # NEVER auto-init plain object

        if isinstance(key, str):
            return _unwrap(self._by_name.get(key, RegistryWrapper(cast(T, default))))

        meta = _get_meta_from_key(key)

        if isinstance(key, type):
            # if a type has metadata attached to it as an attribute,
            # the registry must use that metadata to construct the object
            # or query for a constructed object. This is because the user
            # has intentionally added metadata to the class, and thus
            # we should not use metadata inherited from interfaces.
            if _get_meta(key, include_bases=False) is not None:
                return _unwrap(self._get_by_metadata(meta, default))

            obj_list = self._by_iface.get(key)
            if obj_list:
                return _unwrap(obj_list[0])

        return _unwrap(self._get_by_metadata(meta, default))

    def __getitem__(self, key: "RegistryKey[T]") -> T:
        """Get an object from the registry by a key.
        Parameters:
            key: a string, type, or RegistryDefinition that will be used
                to find (or construct) the desired object.
        Returns:
            The requested object.
        Raises:
            KeyError: if the object is not registered and cannot be generated.
        """
        obj = self.get(key, default=AUTO_OR_NONE)
        if obj is None or obj is AUTO_OR_NONE:
            raise KeyError(key)
        return obj

    def __setitem__(self, key: "RegistryKey[T]", value: T) -> None:
        """Add an object to the registry by a key.

        Parameters:
            key: a string, type, or RegistryDefinition that will be used to
                identify the object.
            value: the object to add to the registry
        """
        if isinstance(key, str):
            self.register(value, name=key)
        elif isinstance(key, type):
            meta = _get_meta(key, include_bases=False)
            if meta is not None:
                # class has registry metadata that can be used to construct it
                self._set_by_metadata(meta, value)

            self.register(value, interfaces=[key])
        elif isinstance(key, RegistryMetadata):
            # self._set_by_metadata(key, RegistryWrapper(value))
            raise KeyError("cannot set value in registry by metadata")
        else:
            raise KeyError(f"invalid key for Registry: {key!r}")

    # TODO __delitem__ (should work same as get/set)
    # TODO __iter__ (should return some sort of (obj, name) structure
