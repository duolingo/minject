"""Collection of annotations to define how a class should be initialized by the registry."""

import itertools
import os
from typing import Any, Callable, Sequence, Type, TypeVar, Union  # pylint: disable=unused-import

import six

from .metadata import RegistryMetadata, _gen_meta, _get_meta
from .model import RegistryKey  # pylint: disable=unused-import
from .model import Deferred, Resolvable, Resolver, resolve_value

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


def bind(_name=None, _start=None, _close=None, **bindings):
    # type: (str, Callable, Callable, Resolvable) -> Callable
    """Decorator to bind values for the init args of a class."""

    def wrap(cls):
        # type: (Type[T]) -> Type[T]
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


def define(base_class, _name=None, _start=None, _close=None, **bindings):
    # type: (Type[T], str, Callable[[T], None], Callable[[T], None], Resolvable) -> RegistryMetadata[T]
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


class _RegistryReference(Deferred[T]):
    """Reference to an object in the registry to be loaded later.
    (you should not instantiate this class directly, instead use the
    inject.reference function)"""

    def __init__(self, key):
        # type: (RegistryKey[T]) -> None
        self._key = key

    def resolve(self, registry_impl):
        # type: (Resolver) -> T
        return registry_impl.resolve(self._key)

    @property
    def key(self):
        # type: () -> RegistryKey[T]
        """The key in the Registry of the object this reference is for.
        This key could be either a class or registry metadata about how
        the object should be constructed."""
        return self._key

    def __str__(self):
        if isinstance(self.key, six.class_types):
            return "ref({})".format(self._key.__name__)
        else:
            return "ref({})".format(self._key)

    def __repr__(self):
        return "<_RegistryReference({!r})>".format(self._key)


def reference(key, **bindings):
    # type: (Type[T], Resolvable) -> _RegistryReference[T]
    """Return a reference to another registry key."""
    if not bindings:
        return _RegistryReference(key)
    elif isinstance(key, type):
        return _RegistryReference(define(key, None, None, None, **bindings))
    else:
        raise TypeError("inject.reference can only include bindings on classes")


class _RegistryFunction(Deferred[T]):
    """Function to call to resolve an initialization argument."""

    def __init__(self, func, *args, **kwargs):
        # type: (Union[str, Callable], Resolvable, Resolvable) -> None
        self._func = func
        self._args = args or ()
        self._kwargs = kwargs or {}

    def resolve(self, registry_impl):
        # type: (Resolver) -> T
        args = []
        for arg in self.args:
            args.append(resolve_value(registry_impl, arg))
        kwargs = {}
        for key, arg in six.iteritems(self.kwargs):
            kwargs[key] = resolve_value(registry_impl, arg)
        return self.func(registry_impl)(*args, **kwargs)

    def func(self, registry_impl):
        # type: (Resolver) -> Callable[..., T]
        if isinstance(self._func, six.string_types):
            # TODO(1.0): deprecated, unnecessary
            # if 'func' is a string use the method with that name
            # on the registry object referenced by arg0
            arg0 = resolve_value(registry_impl, next(iter(self._args)))
            return getattr(arg0, self._func)
        else:
            return self._func

    @property
    def args(self):
        # type: () -> Sequence
        if isinstance(self._func, six.string_types):
            # TODO(1.0): deprecated, unnecessary
            # if 'func' is a string the first argument is used to resolve the method
            # instead of being passed as an argument
            return self._args[1:]
        else:
            return self._args

    @property
    def kwargs(self):
        # type: () -> dict
        return self._kwargs

    def call(self, registry_impl):
        # type: (Resolver) -> T
        return self.resolve(registry_impl)

    def __str__(self):
        return "{}({})".format(
            self._func.__name__,
            ", ".join(
                itertools.chain(
                    (str(arg) for arg in self._args),
                    ("{}={}".format(*item) for item in six.iteritems(self._kwargs)),
                )
            ),
        )

    def __repr__(self):
        return "<_RegistryFunction({!r}(args={!r}, kwargs={!r}))>".format(
            self._func, self._args, self._kwargs
        )


def function(func, *args, **kwargs):
    # type: (Callable[..., T], Any, Any) -> _RegistryFunction[T]
    """Bind a function to be run at init time.
    Parameters:
        func: the function to call, should return a value to bind (this value
            can also be a reference). If func is a string, func will be
            determined by calling getattr on the first positional argument.
        args: positional arguments that should be passed to the function.
        kwargs: keyword arguments that should be passed to the function.
    """
    if isinstance(func, six.string_types):
        if not args:
            raise ValueError(
                "registry.function using a string must have a "
                "positional argument to call getattr on"
            )

    return _RegistryFunction(func, *args, **kwargs)


class _RegistryConfig(Deferred[T]):
    """Reference to a value in the configuration object."""

    def __init__(self, key, default=RAISE_KEY_ERROR, fallback_to_envvar=False):
        # type: (str, Union[T, None, _RaiseKeyError]) -> None
        self._key = key
        self._default = default
        self._fallback_to_envvar = fallback_to_envvar

    def resolve(self, registry_impl):
        # type: (Resolver) -> T
        if self._key in registry_impl.config:
            # first try to resolve the key from the config mapping
            return registry_impl.config[self._key]
        elif self._fallback_to_envvar and self._key in os.environ:
            # then, if allowed, try to fallback to an environment variable
            return os.environ[self._key]
        else:
            # finally fallback to default (which may be to raise a key error)
            if self._default is RAISE_KEY_ERROR:
                raise KeyError(self._key)
            else:
                return self._default

    @property
    def key(self):
        # type: () -> str
        return self._key

    @property
    def default(self):
        # type: () -> Union[T, None, _RaiseKeyError]
        return self._default

    def __str__(self):
        return "config({})".format(self._key)

    def __repr__(self):
        return "<_RegistryConfig({!r})>".format(self._key)


def config(name_, default=RAISE_KEY_ERROR, fallback_to_envvar=False):
    # type: (str, Union[T, None, _RaiseKeyError]) -> _RegistryConfig[T]
    """
    Return a value from the registry config object.

    Parameters:
        name_:
            Name of the configuration value to return
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

    def resolve(self, registry_impl):
        # type: (Resolver) -> Resolver
        return registry_impl


self_tag = _RegistrySelf()
