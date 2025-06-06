"""The Registry itself is a runtime collection of initialized classes."""

import functools
import importlib
import logging
from asyncio import to_thread
from contextlib import AsyncExitStack
from textwrap import dedent
from threading import RLock
from typing import Any, Callable, Dict, Generic, Iterable, List, Mapping, Optional, TypeVar, Union, cast

from typing_extensions import Concatenate, ParamSpec

from minject.inject import _is_key_async, _RegistryReference, reference

from .config import RegistryConfigWrapper, RegistryInitConfig
from .metadata import RegistryMetadata, _get_meta, _get_meta_from_key
from .model import RegistryKey, Resolvable, Resolver, aresolve_value, resolve_value

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


def _unwrap(wrapper: Optional["_RegistryWrapper[T]"]) -> Optional[T]:
    return wrapper.obj if wrapper else None


def _resolve_import(value: str) -> RegistryKey:
    module_name, var_name = value.rsplit(".", 1)
    module = importlib.import_module(module_name)
    return getattr(module, var_name)


class _RegistryWrapper(Generic[T]):
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


def _synchronized(
    func: Callable[Concatenate["Registry", P], R],
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
        self._objects: List[_RegistryWrapper[Any]] = []
        self._by_meta: Dict[RegistryMetadata, _RegistryWrapper[Any]] = {}
        self._by_name: Dict[str, _RegistryWrapper[Any]] = {}
        self._by_iface: Dict[type, List[_RegistryWrapper[Any]]] = {}
        self._config = RegistryConfigWrapper()

        self._lock = RLock()

        self._async_context_stack: AsyncExitStack = AsyncExitStack()
        self._async_entered = False

        if config is not None:
            self._config.from_dict(config)

    @property
    def config(self) -> RegistryConfigWrapper:
        return self._config

    def resolve(self, key: "RegistryKey[T]") -> T:
        return self[key]

    async def _aresolve(self, key: "RegistryKey[T]") -> T:
        result = await self.aget(key)
        if result is None:
            raise KeyError(key, "could not be resolved")
        return result

    async def _push_async_context(self, key: Any) -> Any:
        result = await self._async_context_stack.enter_async_context(key)
        if result is not key:
            raise ValueError(
                dedent(
                    """
                Classes decorated with @async_context must
                return the same value from __aenter__ as they do
                from their constructor. Hint: __aenter__ should
                return self.
                """
                ).strip()
            )

    def _autostart_candidates(self) -> Iterable[RegistryKey]:
        registry_config: Optional[Mapping[str, Any]] = self.config.get("registry")
        if registry_config is not None:
            if (autostart := registry_config.get("autostart")) is not None:
                return (_resolve_import(value) for value in autostart)
        return ()

    @_synchronized
    def start(self) -> None:
        """
        Call start if defined on all objects contained in the registry.
        This includes any classes designated as autostart in config.

        .. deprecated:: 1.0
           This method is deprecated and should not be used in new code.
           Use the context manager API instead.
        """
        for key in self._autostart_candidates():
            LOG.debug("autostarting %s", key)
            _ = self[key]

        for wrapper in list(self._objects):
            if wrapper._meta is not None:
                # call the object's start method, if defined
                wrapper.start()

    @_synchronized
    def close(self) -> None:
        """Close all objects contained in the registry.

        .. deprecated:: 1.0
           This method is deprecated and should not be used in new code.
           Use the context manager API instead.
        """
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

        wrapper = _RegistryWrapper(obj)

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
    ) -> _RegistryWrapper[T]:
        wrapper = _RegistryWrapper(obj, meta)

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

    @_synchronized
    def _remove_by_metadata(
        self, meta: RegistryMetadata[T], wrapper: _RegistryWrapper[T], _global: bool = True
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

    @_synchronized
    def _register_by_metadata(self, meta: RegistryMetadata[T]) -> _RegistryWrapper[T]:
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

    async def _aregister_by_metadata(self, meta: RegistryMetadata[T]) -> _RegistryWrapper[T]:
        """
        async version of _register_by_metadata. Calls _ainit_object instead of _init_object.
        """
        LOG.debug("registering %s", meta)

        # allocate the object (but don't initialize yet)
        obj = meta._new_object()

        # add to the registry (done before init in case of circular reference)
        wrapper = self._set_by_metadata(meta, obj, _global=False)

        success = False
        try:
            # initialize the object
            await meta._ainit_object(obj, self)
            # add to our list of all objects (this MUST happen after init so
            # any references come earlier in sequence and are destroyed first)
            self._objects.append(wrapper)

            # after creating an object, enter the objects context
            # if it is marked with the @async_context decorator.
            if meta.is_async_context:
                await self._push_async_context(obj)

            success = True
        finally:
            if not success:
                self._remove_by_metadata(meta, wrapper, _global=False)

        return wrapper

    @_synchronized
    def _get_by_metadata(
        self, meta: RegistryMetadata[T], default: Optional[Union[T, _AutoOrNone]] = AUTO_OR_NONE
    ) -> Optional[_RegistryWrapper[T]]:
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
        elif meta in self._by_meta:
            return self._by_meta[meta]

        if default is AUTO_OR_NONE:
            return self._register_by_metadata(meta)
        elif default is not None:
            return _RegistryWrapper(cast(T, default))
        else:
            return None

    async def _aget_by_metadata(self, meta: RegistryMetadata[T]) -> Optional[_RegistryWrapper[T]]:
        """
        async version of _get_by_metadata. The default argument has been removed
        from the signature, as there is no use case for it at the time of writing.
        Please make a feature request if you need this functionality.
        """
        if meta in self._by_meta:
            return self._by_meta[meta]

        return await self._aregister_by_metadata(meta)

    @_synchronized
    def __len__(self) -> int:
        return len(self._objects)

    def __contains__(self, key : object) -> bool:
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
        if _is_key_async(key):
            raise AssertionError(
                "cannot use synchronous get on async object (object marked with @async_context)"
            )

        if key == object:
            return None  # NEVER auto-init plain object

        if isinstance(key, str):
            return _unwrap(self._by_name.get(key, _RegistryWrapper(cast(T, default))))

        meta = _get_meta_from_key(key)
        maybe_class = self._get_if_already_in_registry(key, meta)
        if maybe_class is not None:
            return maybe_class

        return _unwrap(self._get_by_metadata(meta, default))

    async def aget(self, key: "RegistryKey[T]") -> Optional[T]:
        """
        Resolve objects marked with the @async_context decorator.
        """
        if not _is_key_async(key):
            raise AssertionError("key must be async to use aget")

        if not self._async_entered:
            raise AssertionError("cannot use aget outside of async context")

        meta = _get_meta_from_key(key)
        maybe_initialized_obj = self._get_if_already_in_registry(key, meta)
        if maybe_initialized_obj is not None:
            return maybe_initialized_obj

        initialized_obj = await self._aget_by_metadata(meta)
        return _unwrap(initialized_obj)

    def _get_if_already_in_registry(
        self, key: "RegistryKey[T]", meta: "RegistryMetadata[T]"
    ) -> Optional[T]:
        # retrieve the class metdata, and the metadata of class
        # without inherited metadata
        meta = _get_meta_from_key(key)

        # if the class has already been registered, return it
        if meta in self._by_meta:
            return _unwrap(self._by_meta[meta])

        # following checks only apply if key is a class
        if not isinstance(key, type):
            return None

        # If the class (key) has no metadata, but an object exists in the
        # registry that is a concrete subtype of the class, return that
        # object. If the class has metadata, we must use the metadata to
        # construct the class, and we should not check the registry for
        # concrete subtypes. A user must specify metadata for a class itself
        # in order to force the registry to use that metadata to construct the
        # class, inherited metadata alone does not prevent the registry
        # from returning a concrete subtype of the class.
        meta_no_bases = _get_meta(key, include_bases=False)
        obj_list = self._by_iface.get(key)
        if meta_no_bases is None and obj_list:
            return _unwrap(obj_list[0])

        # nothing has been registered for this metadata yet
        return None

    async def __aenter__(self) -> "Registry":
        """
        Mark a registry instance as ready for resolving async objects.
        """
        if self._async_entered:
            raise AssertionError(
                "Attempting to enter registry context while already in context. This should not happen."
            )
        self._async_entered = True
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        """
        Closes the registry. Closes all contexts on the registry's context stack
        and then closes the registry itself with regisry.close().
        """
        if not self._async_entered:
            raise AssertionError(
                "Attempting to exit registry context while not in context. This should not happen."
            )
        self._async_entered = False
        # close all objects in the registry
        try:
            await self._async_context_stack.aclose()
        finally:
            # as we currently only support async -> sync transitions,
            # a sync class cannot depend on an async class, and thus we may
            # safely close all sync classes after closing all async classes.
            await to_thread(self.close)

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
