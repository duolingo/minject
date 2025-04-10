from typing import TYPE_CHECKING, Any, Dict, Mapping, Optional, Sequence, TypeVar, Union

from typing_extensions import TypedDict

from .types import Kwargs

if TYPE_CHECKING:
    from .metadata import RegistryMetadata

# Unbound, invariant type variable
T = TypeVar("T")


class RegistrySubConfig(TypedDict, total=False):
    """Configuration entries that apply to the registry itself."""

    # A sequence of class names that should start at registry start time.
    autostart: Sequence[str]
    # Names of registry classes mapped to the kwarg dictionary that should be used to initialize
    # the object of that type.
    by_class: Mapping[str, Kwargs]
    # Named registry entries that map to the kwarg dictionary that should be used to initialize
    # the object for that name.
    by_name: Mapping[str, Kwargs]


class InternalRegistryConfig(TypedDict, total=False):
    registry: RegistrySubConfig


RegistryInitConfig = Union[Mapping[str, Any], InternalRegistryConfig]


class RegistryConfigWrapper:
    """Manages the configuration of the registry."""

    def __init__(self):
        self._impl = {}

    def _from_dict(self, config_dict: RegistryInitConfig):
        """Configure the registry from a dictionary-like mapping.
        The provided mapping should contain general configuration that can
        be accessed using the inject.config decorator.

        Parameters:
            config_dict: the configuration data to apply.
        """
        self._impl = config_dict

    def __contains__(self, key: str):
        return key in self._impl

    def get(self, key: str, default: Optional[T] = None) -> T:
        return self._impl.get(key, default)

    def __getitem__(self, key: str) -> Any:
        item: Optional[Any] = self.get(key)
        if item is None:
            raise KeyError(key)
        return item

    def get_init_kwargs(self, meta: "RegistryMetadata[T]") -> Kwargs:
        """Get init kwargs configured for a given RegistryMetadata."""
        result: Dict[str, Any] = {}

        by_class = self._impl.get("by_class")
        if by_class and meta._cls:
            # first apply config for the class name
            cls_name = meta._cls.__name__
            kwargs = by_class.get(cls_name)
            if kwargs:
                result.update(kwargs)

            # then apply config for the fully qualified class name
            cls_module = f"{meta._cls.__module__}.{cls_name}"
            kwargs = by_class.get(cls_module)
            if kwargs:
                result.update(kwargs)

        # finally apply config for the object by name
        by_name = self._impl.get("by_name")
        if by_name and meta._name:
            kwargs = by_name.get(meta._name)
            if kwargs:
                result.update(kwargs)

        return result
