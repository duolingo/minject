"""Collection of annotations to define how a class should be initialized by the registry."""

import itertools
import os
from asyncio import to_thread
from typing import (
    Any,
    Callable,
    Dict,
    Optional,
    Sequence,
    Type,
    TypeVar,
    Union,
    cast,
    overload,
)

from typing_extensions import TypeGuard, assert_type

from minject.types import _AsyncContext

from .metadata import _INJECT_METADATA_ATTR, RegistryMetadata, _gen_meta, _get_meta
from .model import (
    Deferred,
    DeferredAny,
    RegistryKey,  # pylint: disable=unused-import
    Resolver,
    resolve_value,
)
from .types import _AsyncContext, _MinimalMappingProtocol

T = TypeVar("T")
T_co = TypeVar("T_co", covariant=True)
T_async_context = TypeVar("T_async_context", bound=_AsyncContext)
R = TypeVar("R")


class _RaiseKeyError:
    """
    Placeholder to indicate a method should raise a KeyError instead of returning a default.
    DO NOT instantiate this class directly, instead use the `RAISE_KEY_ERROR` singleton.
    """

    def __nonzero__(self):
        return False

    def __bool__(self):
        return False


# Placeholder to indicate a method should raise a KeyError instead of returning a default.
RAISE_KEY_ERROR = _RaiseKeyError()


# Overload for when we _cannot_ infer what `T` will be from a call to bind
@overload
def bind(
    _name: Optional[str] = None, _start: None = None, _close: None = None, **bindings: DeferredAny
) -> Callable[[Type[T]], Type[T]]:
    ...


# Overload for when we _can_ infer what `T` will be from a call to bind.
@overload
def bind(
    _name: Optional[str] = None,
    _start: Optional[Callable[[T], None]] = None,
    _close: Optional[Callable[[T], None]] = None,
    **bindings: DeferredAny,
) -> Callable[[Type[T]], Type[T]]: ...


def bind(
    _name=None,
    _start=None,
    _close=None,
    **bindings,
):
    """Decorator to bind values for the init args of a class."""

    def wrap(cls: Type[T]) -> Type[T]:
        """Decorate a class with registry bindings."""
        meta = _gen_meta(cls)
        if _name:
            meta._name = _name
        if _start:
            meta._start = _start
        if _close:
            meta._close = _close
        meta.update_bindings(**bindings)
        return cls

    return wrap


def async_context(cls: Type[T_async_context]) -> Type[T_async_context]:
    """
    Declare that a class is as an async context manager
    that can be initialized by the registry through aget(). This
    is to distinguish the class from an async context manager that
    should not be initialized by the registry (an example of
    this being asyncio.Lock).
    """
    meta = _gen_meta(cls)
    meta.is_async_context = True
    return cls

# TODO(1.0): deprecated, not used
def name(name_):
    # type: (str) -> Callable[[Type[T]], Type[T]]
    """Decorator to bind a registry name for a class."""

    def wrap(cls):
        # type: (Type[T]) -> Type[T]
        """Decorate a class with a registry name."""
        meta = _gen_meta(cls)
        meta._name = name_
        return cls

    return wrap


# TODO(1.0): deprecated, not used
def start_method(cls, method):
    # type: (Type[T], Callable[[T], None]) -> None
    """Function to bind a registry start function for a class."""
    if isinstance(cls, RegistryMetadata):
        meta = cls
    else:
        meta = _gen_meta(cls)
    meta._start = method


# TODO(1.0): deprecated, not used
def close_method(cls, method):
    # type: (Type[T], Callable[[T], None]) -> None
    """Function to bind a registry close function for a class."""
    if isinstance(cls, RegistryMetadata):
        meta = cls
    else:
        meta = _gen_meta(cls)
    meta._close = method


def define(
    base_class: Type[T],
    _name: Optional[str] = None,
    _start: Optional[Callable[[T], None]] = None,
    _close: Optional[Callable[[T], None]] = None,
    **bindings: DeferredAny,
) -> RegistryMetadata[T]:
    """Create a new registry key based on a class and optional bindings."""
    meta = _get_meta(base_class)
    if meta:
        meta = RegistryMetadata(
            base_class, is_async_context=meta.is_async_context, bindings=dict(meta.bindings)
        )
        meta.update_bindings(**bindings)
    else:
        meta = RegistryMetadata(base_class, bindings=bindings)
    meta._name = _name
    meta._start = _start
    meta._close = _close
    return meta


def _is_type(key: "RegistryKey[T]") -> TypeGuard[Type[T]]:
    """A typeguard function to see if a RegistryKey[T] is-a Type[T]"""
    return isinstance(key, type)


def _is_key_async(key: "RegistryKey[T]") -> bool:
    """
    Check whether a registry key is an "async", or in other words
    marked for async initialization within the registry with @async_context.
    If a key is "async", it can be initialized through Registry.aget.
    """
    # At present, we only consider objects with RegistryMetadata.is_async_context
    # set to True to be "async", or able to be initialized through Registry.aget.
    # In the future, we likely will support initializing both async and non-async
    # objects through aget, but we are deferring implementing this until
    # we have a bit more experience using the async Registry API.
    if isinstance(key, str):
        return False
    elif isinstance(key, RegistryMetadata):
        return key.is_async_context
    else:
        assert_type(key, Type[T])
        inject_metadata = _get_meta(key)
        if inject_metadata is None:
            return False
        return inject_metadata.is_async_context


class _RegistryReference(Deferred[T_co]):
    """Reference to an object in the registry to be loaded later.
    (you should not instantiate this class directly, instead use the
    inject.reference function)
    """

    def __init__(self, key: "RegistryKey[T_co]") -> None:
        self._key = key

    def resolve(self, registry_impl: Resolver) -> T_co:
        return registry_impl.resolve(self._key)

    async def aresolve(self, registry_impl: Resolver) -> T_co:
        if _is_key_async(self._key):
            return await registry_impl._aresolve(self._key)
        return await to_thread(registry_impl.resolve, self._key)

    @property
    def type_of_object_referenced_in_key(self) -> "Type[T_co]":
        if type(self.key) == RegistryMetadata:
            try:
                return self.key.interfaces[0]
            except IndexError:
                raise TypeError("Unable to fetch type of key, no interface.")
        elif type(self.key) == type:
            return self.key

        elif type(self.key) == str:
            raise TypeError(
                "The Key is a string. No object is being referenced from within the key itself."
            )

        else:
            raise TypeError("The Key is neither a string, type, or RegistryMetadata")

    @property
    def key(self) -> "RegistryKey[T_co]":
        """The key in the Registry of the object this reference is for.
        This key could be either a class or registry metadata about how
        the object should be constructed.
        """
        return self._key

    def __str__(self) -> str:
        if _is_type(self._key):
            return f"ref({self._key.__name__})"
        else:
            return f"ref({self._key})"

    def __repr__(self) -> str:
        return f"<_RegistryReference({self._key!r})>"


@overload
def reference(key: RegistryMetadata[T]) -> _RegistryReference[T]: ...


@overload
def reference(key: str) -> _RegistryReference: ...


@overload
def reference(key: Type[T], **bindings: DeferredAny) -> _RegistryReference[T]: ...


def reference(key, **bindings):
    """Return a reference to another registry key."""
    if not bindings:
        return _RegistryReference(key)
    elif isinstance(key, type):
        return _RegistryReference(define(key, None, None, None, **bindings))
    else:
        raise TypeError("inject.reference can only include bindings on classes")


class _RegistryFunction(Deferred[T_co]):
    """Function to call to resolve an initialization argument."""

    def __init__(
        self,
        func: Union[str, Callable[..., T_co]],
        # TODO: Type with ParamSpec and Concatenate after those are supported by mypy.
        #    https://github.com/python/mypy/issues/10201
        *args: DeferredAny,
        **kwargs: DeferredAny,
    ):
        self._func = func
        self._args = args or ()
        self._kwargs = kwargs or {}

    def resolve(self, registry_impl: Resolver) -> T_co:
        args = []
        for arg in self.args:
            args.append(resolve_value(registry_impl, arg))
        kwargs = {}
        for key, arg in self.kwargs.items():
            kwargs[key] = resolve_value(registry_impl, arg)
        return self.func(registry_impl)(*args, **kwargs)

    async def aresolve(self, registry_impl: Resolver) -> T_co:
        raise NotImplementedError("Have not implemented async registry function")

    def func(self, registry_impl: Resolver) -> Callable[..., T_co]:
        if isinstance(self._func, str):
            # TODO(1.0): deprecated, unnecessary
            # if 'func' is a string use the method with that name
            # on the registry object referenced by arg0
            arg0 = resolve_value(registry_impl, next(iter(self._args)))
            return getattr(arg0, self._func)
        else:
            return self._func

    @property
    def args(self) -> Sequence[DeferredAny]:
        if isinstance(self._func, str):
            # TODO(1.0): deprecated, unnecessary
            # if 'func' is a string the first argument is used to resolve the method
            # instead of being passed as an argument
            return self._args[1:]
        else:
            return self._args

    @property
    def kwargs(self) -> Dict[str, DeferredAny]:
        return self._kwargs

    def call(self, registry_impl: Resolver) -> T_co:
        return self.resolve(registry_impl)

    def __str__(self) -> str:
        return "{}({})".format(
            self._func if isinstance(self._func, str) else self._func.__name__,
            ", ".join(
                itertools.chain(
                    (str(arg) for arg in self._args),
                    ("{}={}".format(*item) for item in self._kwargs.items()),
                )
            ),
        )

    def __repr__(self) -> str:
        return f"<_RegistryFunction({self._func!r}(args={self._args!r}, kwargs={self._kwargs!r}))>"


def function(
    func: Union[str, Callable[..., T]], *args: DeferredAny, **kwargs: DeferredAny
) -> _RegistryFunction[T]:
    """Bind a function to be run at init time.
    Parameters:
        func: the function to call, should return a value to bind (this value
            can also be a reference). If func is a string, func will be
            determined by calling getattr on the first positional argument.
        args: positional arguments that should be passed to the function.
        kwargs: keyword arguments that should be passed to the function.
    """
    if isinstance(func, str):
        if not args:
            raise ValueError(
                "registry.function using a string must have a "
                "positional argument to call getattr on"
            )

    return _RegistryFunction(func, *args, **kwargs)


def _is_key_error(obj: Any) -> TypeGuard[_RaiseKeyError]:
    return obj is RAISE_KEY_ERROR


class _RegistryConfig(Deferred[T_co]):
    """Reference to a value in the configuration object."""

    def __init__(
        self,
        key: Optional[str],
        default: Union[T_co, _RaiseKeyError] = RAISE_KEY_ERROR,
        fallback_to_envvar: bool = False,
    ) -> None:
        self._key = key
        self._default = default
        self._fallback_to_envvar = fallback_to_envvar

    def resolve(self, registry_impl: Resolver) -> T_co:
        if self._key is None:
            return cast(
                T_co, registry_impl.config
            )  # If _key is None then T is RegistryConfigWrapper
        if self._key in registry_impl.config:
            # first try to resolve the key from the config mapping
            return registry_impl.config[self._key]
        if self._fallback_to_envvar and self._key in os.environ:
            # then, if allowed, try to fallback to an environment variable
            return cast(T_co, os.environ[self._key])

        # finally fallback to default (which may be to raise a key error)
        if _is_key_error(self._default):
            raise KeyError(self._key)
        else:
            return cast(T_co, self._default)

    async def aresolve(self, registry_impl: Resolver) -> T_co:
        return await to_thread(self.resolve, registry_impl)

    @property
    def key(self) -> Optional[str]:
        return self._key

    @property
    def default(self) -> Optional[Union[T_co, _RaiseKeyError]]:
        return self._default

    def __str__(self) -> str:
        return f"config({self._key})"

    def __repr__(self) -> str:
        return f"<_RegistryConfig({self._key!r})>"


class _RegistryNestedConfig(Deferred[T_co]):
    def __init__(
        self,
        keys: Union[Sequence[str], str],
        default: Union[T_co, _RaiseKeyError] = RAISE_KEY_ERROR,
    ) -> None:
        """
        Allows simpler injection of nested config values.
        This is similar to the `Config.get_nested` call, but allows for lazy loading of the config
        values (as is done with other injected values by the registry).

        See Also:
            The `nested_config` method's documentation for more information on parameters, etc.
        """
        self._keys: Sequence[str] = keys.split(".") if isinstance(keys, str) else keys
        self._default = default

    def resolve(self, registry_impl: Resolver) -> T_co:
        sub = registry_impl.config
        for key in self._keys:
            if isinstance(sub, _MinimalMappingProtocol) and key in sub:
                sub = sub[key]
            elif isinstance(self._default, _RaiseKeyError):
                raise KeyError(self._keys)
            else:
                return self._default
        return cast(T_co, sub)

    async def aresolve(self, registry_impl: Resolver) -> T_co:
        return await to_thread(self.resolve, registry_impl)


def nested_config(
    keys: Union[Sequence[str], str], default: Union[T, _RaiseKeyError] = RAISE_KEY_ERROR
) -> _RegistryNestedConfig[T]:
    """
    Returns a reference to a nested registry config value.

    The difference betewen using this and an immediate
    `inject.bind(param=Config.load_config().get_nested(keys))` is that the config value will be
    loaded only when it is needed - like the rest of the registry references.
    Additionally, you have the guarantee that the config value will come from the same config the
    registry is using.

    Parameters:
        keys: This can be a sequence of names like `Config.get_nested`, or it can be a dotted name
            like "my.nested.config.value". Such strings are split on the "." character.  If you
            have a name that contains a period you will need to pass in keys as a pre-split sequence
            of names.
        default: The default to return if the key is not set/does not exist.
            If it is the special value `RAISE_KEY_ERROR` then no default is returned and a key error
            is raised. Defaults to RAISE_KEY_ERROR.

    Returns:
        A reference to the config value that will be lazy-loaded.
    """
    return _RegistryNestedConfig(keys, default)


def config(
    name_: Optional[str] = None,
    default: Union[T, _RaiseKeyError] = RAISE_KEY_ERROR,
    fallback_to_envvar: bool = False,
) -> _RegistryConfig[T]:
    """
    Return a value from the registry config object.

    Parameters:
        name_:
            Name of the configuration value to return, if None return config object itself.
        default:
            Default value to return when name does not exist, use RAISE_KEY_ERROR to fail.
        fallback_to_envvar:
            True to fallback to the same name environment variable if not in config.

    Returns:
        A deferred value that the registry will resolve to given named config value.

    Raises:
        KeyError: The given name is not found and no default is provided (RAISE_KEY_ERROR)
    """
    return _RegistryConfig(name_, default, fallback_to_envvar)


class _RegistrySelf(Deferred[Resolver]):
    """Reference to the Registry instance itself."""

    def resolve(self, registry_impl: Resolver) -> Resolver:
        return registry_impl

    async def aresolve(self, registry_impl: Resolver) -> Resolver:
        return await to_thread(self.resolve, registry_impl)


self_tag = _RegistrySelf()
