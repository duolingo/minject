from typing import TYPE_CHECKING, Any, Mapping, Optional, Sequence, TypeVar, Union

from typing_extensions import TypedDict

from .types import Kwargs

if TYPE_CHECKING:
    from .metadata import RegistryMetadata

# Unbound, invariant type variable
T = TypeVar("T")


class _RegistrySubConfig(TypedDict, total=False):
    """Configuration entries that apply to the registry itself."""

    # A sequence of class names that should start at registry start time.
    autostart: Sequence[str]
    # Names of registry classes mapped to the kwarg dictionary that should be used to initialize
    # the object of that type.
    by_class: Mapping[str, Kwargs]
    # Named registry entries that map to the kwarg dictionary that should be used to initialize
    # the object for that name.
    by_name: Mapping[str, Kwargs]


class _InternalRegistryConfig(TypedDict, total=False):
    registry: _RegistrySubConfig


RegistryInitConfig = Union[Mapping[str, Any], _InternalRegistryConfig]


class RegistryConfigWrapper:
    """Manages the configuration of the registry."""

    def __init__(self):
        self._impl = {}

    def from_dict(self, config_dict: Union[Mapping[str, Any], _InternalRegistryConfig]):
        """Configure the registry from a dictionary.

        .. deprecated:: 1.0
           This method is deprecated and should not be used in new code.
           Use the config parameter to Registry instead to specify config dictionaries.

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
