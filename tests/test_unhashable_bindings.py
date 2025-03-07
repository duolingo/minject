from minject import initialize, inject


class UnhashableDict(dict):
    """A dict subclass that's explicitly not hashable."""

    __hash__ = None  # Make this class explicitly unhashable


def test_unhashable_binding():
    """Test that an unhashable object can be used in a binding."""
    unhashable_obj = UnhashableDict({"key": "value"})

    @inject.bind(config=unhashable_obj)
    class ConfigConsumer:
        def __init__(self, config):
            self.config = config

    registry = initialize()
    config_consumer = registry[ConfigConsumer]

    # Verify that the binding worked correctly
    assert config_consumer.config is unhashable_obj


def test_nested_unhashable_binding():
    """Test that an unhashable object works in a multi-level binding."""
    unhashable_obj = UnhashableDict({"key": "value"})

    @inject.bind(config=unhashable_obj)
    class ConfigProvider:
        def __init__(self, config):
            self.config = config

    @inject.bind(provider=inject.reference(ConfigProvider))
    class ConfigConsumer:
        def __init__(self, provider):
            self.provider = provider

    registry = initialize()
    config_consumer = registry[ConfigConsumer]

    # Verify the bindings worked through multiple levels
    assert config_consumer.provider.config is unhashable_obj
