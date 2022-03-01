"""Collection of annotations to define how a class should be initialized by the registry."""

import itertools
import os
from typing import Any, Callable, Dict, Optional, Sequence, Type, TypeVar, Union, cast, overload

from typing_extensions import TypeGuard

from .metadata import RegistryMetadata, _gen_meta, _get_meta
from .model import RegistryKey  # pylint: disable=unused-import
from .model import Deferred, DeferredAny, Resolver, resolve_value

T = TypeVar("T")
R = TypeVar("R")


class _RaiseKeyError:
    """
    Placeholder to indicate a method should raise a KeyError instead of returning a default.
    DO NOT instantiate this class directly, instead use the `RAISE_KEY_ERROR` singleton.
    """

    def __nonzero__(self):
        return False

    def __bool__(self):  # noqa:E301
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
) -> Callable[[Type[T]], Type[T]]:
    ...


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
        meta = RegistryMetadata(base_class, bindings=dict(meta.bindings))
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


class _RegistryReference(Deferred[T]):
    """Reference to an object in the registry to be loaded later.
    (you should not instantiate this class directly, instead use the
    inject.reference function)"""

    def __init__(self, key: "RegistryKey[T]") -> None:
        self._key = key

    def resolve(self, registry_impl: Resolver) -> T:
        return registry_impl.resolve(self._key)

    @property
    def key(self) -> "RegistryKey[T]":
        """The key in the Registry of the object this reference is for.
        This key could be either a class or registry metadata about how
        the object should be constructed."""
        return self._key

    def __str__(self) -> str:
        if _is_type(self._key):
            return "ref({})".format(self._key.__name__)
        else:
            return "ref({})".format(self._key)

    def __repr__(self) -> str:
        return "<_RegistryReference({!r})>".format(self._key)


@overload
def reference(key: RegistryMetadata[T]) -> _RegistryReference[T]:
    ...


@overload
def reference(key: str) -> _RegistryReference:
    ...


@overload
def reference(key: Type[T], **bindings: DeferredAny) -> _RegistryReference[T]:
    ...


def reference(key, **bindings):
    """Return a reference to another registry key."""
    if not bindings:
        return _RegistryReference(key)
    elif isinstance(key, type):
        return _RegistryReference(define(key, None, None, None, **bindings))
    else:
        raise TypeError("inject.reference can only include bindings on classes")


class _RegistryFunction(Deferred[T]):
    """Function to call to resolve an initialization argument."""

    def __init__(
        self,
        func: Union[str, Callable[..., T]],
        # TODO: Type with ParamSpec and Concatenate after those are supported by mypy.
        #    https://github.com/python/mypy/issues/10201
        *args: DeferredAny,
        **kwargs: DeferredAny,
    ):
        self._func = func
        self._args = args or ()
        self._kwargs = kwargs or {}

    def resolve(self, registry_impl: Resolver) -> T:
        args = []
        for arg in self.args:
            args.append(resolve_value(registry_impl, arg))
        kwargs = {}
        for key, arg in self.kwargs.items():
            kwargs[key] = resolve_value(registry_impl, arg)
        return self.func(registry_impl)(*args, **kwargs)

    def func(self, registry_impl: Resolver) -> Callable[..., T]:
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

    def call(self, registry_impl: Resolver) -> T:
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
        return "<_RegistryFunction({!r}(args={!r}, kwargs={!r}))>".format(
            self._func, self._args, self._kwargs
        )


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


class _RegistryConfig(Deferred[T]):
    """Reference to a value in the configuration object."""

    def __init__(
        self,
        key: Optional[str],
        default: Union[T, _RaiseKeyError] = RAISE_KEY_ERROR,
        fallback_to_envvar: bool = False,
    ) -> None:
        self._key = key
        self._default = default
        self._fallback_to_envvar = fallback_to_envvar

    def resolve(self, registry_impl: Resolver) -> T:
        if self._key is None:
            return cast(T, registry_impl.config)  # If _key is None then T is RegistryConfigWrapper
        if self._key in registry_impl.config:
            # first try to resolve the key from the config mapping
            return registry_impl.config[self._key]
        if self._fallback_to_envvar and self._key in os.environ:
            # then, if allowed, try to fallback to an environment variable
            return cast(T, os.environ[self._key])

        # finally fallback to default (which may be to raise a key error)
        if _is_key_error(self._default):
            raise KeyError(self._key)
        else:
            return cast(T, self._default)

    @property
    def key(self) -> Optional[str]:
        return self._key

    @property
    def default(self) -> Optional[Union[T, _RaiseKeyError]]:
        return self._default

    def __str__(self) -> str:
        return "config({})".format(self._key)

    def __repr__(self) -> str:
        return "<_RegistryConfig({!r})>".format(self._key)


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


self_tag = _RegistrySelf()
