import unittest

import mock

from duolingo_base import registry
from duolingo_base.registry import inject


@inject.bind(
    required=inject.config("REQUIRED"),
    optional=inject.config("OPTIONAL", default=None),
    envvar=inject.config("ENVVAR", fallback_to_envvar=True),
)
class Configable(object):
    def __init__(self, required, optional, envvar):
        self.required = required
        self.optional = optional
        self.envvar = envvar


class RegistryConfigTestCase(unittest.TestCase):
    def setUp(self):
        self.registry = registry.initialize()

    def test_config_simple(self):
        self.registry.config.from_dict({"REQUIRED": 1, "OPTIONAL": 2, "ENVVAR": 3})

        config = self.registry[Configable]
        self.assertEqual(1, config.required)
        self.assertEqual(2, config.optional)
        self.assertEqual(3, config.envvar)

    def test_config_required(self):
        self.registry.config.from_dict({"OPTIONAL": 2, "ENVVAR": 3})

        with (self.assertRaises(KeyError)):
            _ = self.registry[Configable]

    def test_config_optional(self):
        self.registry.config.from_dict({"REQUIRED": 1, "ENVVAR": 3})

        config = self.registry[Configable]
        self.assertEqual(1, config.required)
        self.assertIsNone(config.optional)
        self.assertEqual(3, config.envvar)

    def test_config_envvar(self):
        self.registry.config.from_dict({"REQUIRED": 1, "OPTIONAL": 2})

        with mock.patch.dict("os.environ", {"ENVVAR": "value"}):
            config = self.registry[Configable]
            self.assertEqual(1, config.required)
            self.assertEqual(2, config.optional)
            self.assertEqual("value", config.envvar)

    def test_config_envvar_missing(self):
        self.registry.config.from_dict({"REQUIRED": 1, "OPTIONAL": 2})

        with (self.assertRaises(KeyError)):
            _ = self.registry[Configable]


if __name__ == "__main__":
    unittest.main()
