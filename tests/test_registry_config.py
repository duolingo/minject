from typing import Any, Optional
from unittest import mock

import pytest

from minject import inject, registry
from minject.inject import _RegistryConfig
from minject.registry import Registry


@inject.bind(
    required=inject.config("REQUIRED"),
    optional=inject.config("OPTIONAL", default=None),
    envvar=inject.config("ENVVAR", fallback_to_envvar=True),
)
class Configable:
    def __init__(self, required, optional, envvar):
        self.required = required
        self.optional = optional
        self.envvar = envvar


class SingleConfigable:
    def __init__(self, required):
        self.required = required


def test_config_simple() -> None:
    config = {"REQUIRED": 1, "OPTIONAL": 2, "ENVVAR": 3}
    reg = registry.initialize(config)

    config = reg[Configable]
    assert config.required == 1
    assert config.optional == 2
    assert config.envvar == 3


def test_config_required() -> None:
    config = {"OPTIONAL": 2, "ENVVAR": 3}
    reg = registry.initialize(config)

    with pytest.raises(KeyError):
        _ = reg[Configable]


def test_config_optional() -> None:
    config = {"REQUIRED": 1, "ENVVAR": 3}
    reg = registry.initialize(config)

    config = reg[Configable]
    assert config.required == 1
    assert config.optional is None
    assert config.envvar == 3


def test_config_envvar() -> None:
    config = {"REQUIRED": 1, "OPTIONAL": 2}
    reg = registry.initialize(config)

    with mock.patch.dict("os.environ", {"ENVVAR": "value"}):
        config = reg[Configable]
        assert config.required == 1
        assert config.optional == 2
        assert config.envvar == "value"


def test_config_envvar_missing() -> None:
    config = {"REQUIRED": 1, "OPTIONAL": 2}
    reg = registry.initialize(config)

    with pytest.raises(KeyError):
        _ = reg[Configable]


def test_config_default_typing() -> None:
    config = {"EXISTS": "exists"}
    reg = registry.initialize(config)
    temp: _RegistryConfig[Optional[str]] = inject.config("DNE", None)
    assert temp.resolve(reg) is None
    temp = inject.config("EXISTS", None)
    assert temp.resolve(reg) == "exists"


@pytest.mark.parametrize(
    ("nested_config_key",),
    (
        ("top.middle.base",),
        (("top", "middle", "base"),),
    ),
    ids=("dotted string", "string sequence"),
)
def test_nested_config(nested_config_key: Any) -> None:
    config = {"top": {"middle": {"base": "value"}}}
    reg = registry.initialize(config)

    NestedConfigable = inject.define(
        SingleConfigable, required=inject.nested_config(nested_config_key)
    )
    config = reg[NestedConfigable]
    assert config.required == "value"


@pytest.mark.parametrize(
    ("nested_config_key",),
    (("DOES_NOT_EXIST",), ("EXISTS.DOES_NOT_EXIST",), (("EXISTS", "DOES_NOT_EXIST"),)),
    ids=("top level", "sub-item dotted", "sub-item sequence"),
)
def test_nested_config_key_dne(nested_config_key: Any) -> None:
    reg = {"EXISTS": "exists"}
    reg = registry.initialize(reg)

    NestedConfigable = inject.define(
        SingleConfigable, required=inject.nested_config(nested_config_key)
    )
    with pytest.raises(KeyError):
        reg[NestedConfigable]  # pylint: disable=pointless-statement


@pytest.mark.parametrize(
    ("nested_config_key",),
    (("DOES_NOT_EXIST",), ("EXISTS.DOES_NOT_EXIST",), (("EXISTS", "DOES_NOT_EXIST"),)),
    ids=("top level", "sub-item dotted", "sub-item sequence"),
)
def test_nested_config_key_dne_with_default(nested_config_key: Any) -> None:
    reg = {"EXISTS": "exists"}
    reg = registry.initialize(reg)

    NestedConfigable = inject.define(
        SingleConfigable, required=inject.nested_config(nested_config_key, default="DEFAULT")
    )
    config = reg[NestedConfigable]
    assert config.required == "DEFAULT"


if __name__ == "__main__":
    pytest.main()
