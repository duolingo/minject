from minject import inject


@inject.bind(name="Douglas")
class Adult:
    def __init__(self, name):
        self.name = name

    def print_name(self):
        print(self.name)


@inject.bind(parent=inject.reference(Adult))
class Child:
    def __init__(self, parent):
        self.parent = parent

    def print_parent(self):
        self.parent.print_name()

    def get_free_car(self):
        self.parent.buy_car_for_child()


from minject.mock import mock

mocked = mock(Child)
mocked.parent.print_name.assert_not_called()
mocked.print_parent()
mocked.parent.print_name.assert_called_once()

spoiled = True
try:
    mocked.get_free_car()
except AttributeError:
    spoiled = False
assert not spoiled

from unittest.mock import MagicMock, Mock

mocked_1 = mock(Child)

assert isinstance(mocked_1.parent, MagicMock)

mocking_function = lambda binding: Mock(spec=binding)
mocked_2 = mock(Child, mocking_function)

assert isinstance(mocked_2.parent, Mock)


print("Mocking Tests Passed!")
