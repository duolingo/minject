"""The Registry itself is a runtime collection of initialized classes."""

import importlib
import logging
from typing import Dict, Generic, Iterable, List, Optional, TypeVar, Union, cast

from .config import RegistryConfigWrapper, RegistrySubConfig
from .metadata import RegistryMetadata, _get_meta
from .model import RegistryKey, Resolvable, Resolver, resolve_value

LOG = logging.getLogger(__name__)

T = TypeVar("T")


class _AutoOrNone:
    def __nonzero__(self):
        return False

    def __bool__(self):  # noqa:E301
        return False


AUTO_OR_NONE = _AutoOrNone()


def initialize() -> "Registry":
    """Initialize a new registry instance."""
    LOG.debug("initializing a new registry instance")
    return Registry()


def _unwrap(wrapper: Optional["RegistryWrapper[T]"]) -> Optional[T]:
    return wrapper.obj if wrapper else None


def _resolve_import(value: str) -> RegistryKey:
    module_name, var_name = value.rsplit(".", 1)
    module = importlib.import_module(module_name)
    return getattr(module, var_name)


class RegistryWrapper(Generic[T]):
    """Simple wrapper around registered objects for tracking."""

    def __init__(self, obj: T, _meta: Optional[RegistryMetadata[T]] = None) -> None:
        self.obj = obj
        self._meta = _meta

    def start(self) -> None:
        if not getattr(self, "_started", False) and self._meta:
            self._meta._start_object(self.obj)
        self._started = True

    def close(self) -> None:
        if getattr(self, "_started", False):
            if not getattr(self, "_closed", False) and self._meta:
                self._meta._close_object(self.obj)
            self._closed = True


class Registry(Resolver):
    """Tracks and manages registered object instances."""

    def __init__(self):
        self._objects: List[RegistryWrapper] = []
        self._by_meta: Dict[RegistryMetadata, RegistryWrapper] = {}
        self._by_name: Dict[str, RegistryWrapper] = {}
        self._by_iface: Dict[type, List[RegistryWrapper]] = {}

        self._config = RegistryConfigWrapper()

    @property
    def config(self) -> RegistryConfigWrapper:
        return self._config

    def resolve(self, key: "RegistryKey[T]") -> T:
        return self[key]

    def _resolve(self, value: Resolvable[T]) -> T:
        return resolve_value(self, value)

    def _autostart_candidates(self) -> Iterable[RegistryKey]:
        registry_config: Optional[RegistrySubConfig] = self.config.get("registry")
        if registry_config:
            autostart = registry_config.get("autostart")
            if autostart:
                return (_resolve_import(value) for value in autostart)
        return ()

    def start(self) -> None:
        """
        Call start if defined on all objects contained in the registry.
        This includes any classes designated as autostart in config.
        """
        for key in self._autostart_candidates():
            LOG.debug("autostarting %s", key)
            self[key]  # pylint: disable=pointless-statement

        for wrapper in list(self._objects):
            if wrapper._meta is not None:
                # call the object's start method, if defined
                wrapper.start()

    def close(self) -> None:
        """Close all objects contained in the registry."""
        for wrapper in list(reversed(self._objects)):
            if wrapper._meta is not None:
                # call the object's close method, if defined
                wrapper.close()

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

    def _set_by_metadata(
        self, meta: RegistryMetadata[T], obj: T, _global: bool = True
    ) -> RegistryWrapper[T]:
        wrapper = RegistryWrapper(obj, meta)

        if _global:
            self._objects.append(wrapper)
        if meta.name:
            self._by_name[meta.name] = wrapper
        else:
            self._by_meta[meta] = wrapper
        if meta.interfaces:
            for iface in meta.interfaces:
                obj_list = self._by_iface.setdefault(iface, [])
                obj_list.append(wrapper)

        return wrapper

    def _remove_by_metadata(
        self, meta: RegistryMetadata[T], wrapper: RegistryWrapper[T], _global: bool = True
    ) -> None:
        if _global:
            self._objects.remove(wrapper)
        if meta.name:
            del self._by_name[meta.name]
        else:
            del self._by_meta[meta]
        if meta.interfaces:
            for iface in meta.interfaces:
                obj_list = self._by_iface.get(iface)
                if obj_list:
                    obj_list.remove(wrapper)

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
            # call start method (if any)
            wrapper.start()
            success = True
        finally:
            if not success:
                self._remove_by_metadata(meta, wrapper, _global=False)

        return wrapper

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
        # see if a metadata name is provided
        if meta.name:
            if meta.name in self._by_name:
                return self._by_name[meta.name]
        else:
            if meta in self._by_meta:
                return self._by_meta[meta]

        if default is AUTO_OR_NONE:
            return self._register_by_metadata(meta)
        elif default is not None:
            return RegistryWrapper(cast(T, default))
        else:
            return None

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
            raise KeyError("invalid key for Registry: {!r}".format(key))

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
        if isinstance(key, str):
            return _unwrap(self._by_name.get(key, RegistryWrapper(cast(T, default))))
        elif isinstance(key, type):
            meta = _get_meta(key, include_bases=False)
            if meta is not None:
                # class has registry metadata that can be used to construct it
                return _unwrap(self._get_by_metadata(meta, default))

            # TODO: we need to lock!!!!
            obj_list = self._by_iface.get(key)
            if obj_list:
                return _unwrap(obj_list[0])
            else:
                if key == object:
                    return None  # NEVER auto-init plain object

                base = _get_meta(key, include_bases=True)
                if base is not None:
                    meta = RegistryMetadata(key, bindings=dict(base.bindings))
                else:
                    meta = RegistryMetadata(key)
                return _unwrap(self._get_by_metadata(meta, default))
        elif isinstance(key, RegistryMetadata):
            return _unwrap(self._get_by_metadata(key, default))
        else:
            raise KeyError("invalid key for Registry: {!r}".format(key))

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
            raise KeyError("invalid key for Registry: {!r}".format(key))

    # TODO __delitem__ (should work same as get/set)
    # TODO __iter__ (should return some sort of (obj, name) structure
