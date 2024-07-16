from typing import TYPE_CHECKING, Any, Dict, Optional, TypeVar

from typing_extensions import TypedDict

from .types import Kwargs

if TYPE_CHECKING:
    from .metadata import RegistryMetadata

# Unbound, invariant type variable
T = TypeVar("T")


RegistryInitConfig = Dict[str, Any]


class RegistryConfigWrapper:
    """Manages the configuration of the registry."""

    def __init__(self):
        self._impl = {}

    def _from_dict(self, config_dict: RegistryInitConfig):
        """Configure the registry from a dictionary.
        The provided dictionary should contain general configuration that can
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
