import importlib
from typing import TYPE_CHECKING, Any, Callable, Mapping, Optional, TypeVar

from typing_extensions import TypedDict

from .types import Kwargs

if TYPE_CHECKING:
    from .metadata import RegistryMetadata

# Unbound, invariant type variable
T = TypeVar("T")


RegistryInitConfig = Mapping[str, Any]


class RegistryConfigWrapper:
    """Manages the configuration of the registry."""

    def __init__(self, autostart: Callable[[], None] = lambda : None):
        self._impl = {}
        self._autostart = autostart

    def from_dict(self, config_dict: RegistryInitConfig) -> "RegistryConfigWrapper":
        """
        Deprecated: Support legacy minject API. Do not use this in new code.
        """
        self._from_dict(config_dict)

    def _from_dict(self, config_dict: RegistryInitConfig):
        """Configure the registry from a dictionary-like mapping.
        The provided mapping should contain general configuration that can
        be accessed using the inject.config decorator.

        Parameters:
            config_dict: the configuration data to apply.
        """
        self._impl = config_dict

        # to support legacy behavior of auto starting registry instances
        self._autostart()

    def __contains__(self, key: str):
        return key in self._impl

    def get(self, key: str, default: Optional[T] = None) -> T:
        return self._impl.get(key, default)

    def __getitem__(self, key: str) -> Any:
        item: Optional[Any] = self.get(key)
        if item is None:
            raise KeyError(key)
        return item
