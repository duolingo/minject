from typing import Optional, TypeVar
from unittest.mock import MagicMock

from .inject import _RegistryReference
from .metadata import _get_meta_from_key
from .model import MockingFunction, RegistryKey

T = TypeVar("T")


DEFAULT_MOCKING_FUNCTION: MockingFunction = lambda arg: MagicMock(spec=arg)


def mock(key: "RegistryKey[T]", mocking_function: Optional[MockingFunction] = None) -> T:
    """
    Given a RegistryKey key, instantiate the class specified in the key
    with mock constructor arguments corresponding to the key's metadata
    bindings.

    Return a tuple containing the instance and a dictionary of the
    mocks used to instantiate it.
    """
    mocking_f = mocking_function or DEFAULT_MOCKING_FUNCTION

    meta_to_mock = _get_meta_from_key(key)
    kwargs_to_mocks = {}
    class_instantiated_with_mocks = None

    for kwarg, binding in meta_to_mock.bindings.items():
        # if the binding is a RegistryReference, we
        # need to get the type of the referenced object
        if type(binding) == _RegistryReference:
            binding = binding.type_of_object_referenced_in_key
        # if the binding is not already a type, cast v to it's type
        elif type(binding) != type:
            binding = type(binding)
        kwargs_to_mocks[kwarg] = mocking_f(binding)
    try:
        iface = meta_to_mock.interfaces[0]
        class_instantiated_with_mocks = iface(**kwargs_to_mocks)
    except TypeError:
        raise TypeError(
            f"Unable to instantiate class {meta_to_mock.key}"
            "with mocks. Provided arguments do not match class"
            "signature.\n"
            f"arguments: {kwargs_to_mocks}\n"
            f"signature: {iface}"
        )
    except IndexError:
        raise IndexError(
            "Unable to instantiate class {meta_to_mock.name} with mocks. Object does not have an interface."
        )

    return class_instantiated_with_mocks


class MockingError(Exception):
    pass
