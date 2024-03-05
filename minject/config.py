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


class RegistryConfigWrapper:
    """Manages the configuration of the registry."""

    def __init__(self):
        self._impl = {}

    def from_dict(self, config_dict: Union[Dict[str, Any], InternalRegistryConfig]):
        """Configure the registry from a dictionary.
        The provided dictionary should contain general configuration that can
        be accessed using the inject.config decorator. If the key 'registry'
        is present in the dict, it will be used to configure the registry
        itself. The following elements are recognized by the registry:
            autostart: list of classes or names that the registry should
                start by default.
            by_class: dict of registry classes which map to a dict of
                kwargs for initializing any object of that type.
            by_name: dict of named registry entries which map to a dict of
                kwargs for initializing that object.
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

        reg_conf: Optional[RegistrySubConfig] = self._impl.get("registry")
        if reg_conf:
            by_class = reg_conf.get("by_class")
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
            by_name = reg_conf.get("by_name")
            if by_name and meta._name:
                kwargs = by_name.get(meta._name)
                if kwargs:
                    result.update(kwargs)

        return result
