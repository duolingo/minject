# Add imports
from minject import Registry, inject

registry = Registry()


@inject.bind(other_number=10)
class AddToNumber:
    def __init__(self, other_number: int):
        self.other_number = other_number

    def add_to_number(self, number: int):
        return number + self.other_number


add_to_number = registry[AddToNumber]
result = add_to_number.add_to_number(5)
print(result)
assert result == 15
