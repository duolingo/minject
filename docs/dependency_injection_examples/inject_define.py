from abc import ABC
from typing import Tuple, Type

from minject import inject
from minject.inject_attrs import inject_define, inject_field
from minject.registry import Registry


class AbstractAdult(ABC):
    name: str
    age: int


class AbstractChild(ABC):
    age: int
    hobby: str


def before_refactor() -> Tuple[Type[AbstractAdult], Type[AbstractChild]]:
    @inject.bind(name="Bonnie", age=40)
    class Adult(AbstractAdult):
        def __init__(self, name: str, age: int = 30):
            self.name = name
            self.age = age

    @inject.bind(age=15, hobby="Skateboarding")
    class Child(AbstractChild):
        def __init__(self, age: int, hobby: str):
            self.age = age
            self.hobby = hobby

    return Adult, Child


def after_refactor() -> Tuple[Type[AbstractAdult], Type[AbstractChild]]:
    @inject_define
    class Adult(AbstractAdult):
        name: str = inject_field(binding="Bonnie")
        age: int = inject_field(default=30, binding=40)

    @inject_define
    class Child(AbstractChild):
        age: int = inject_field(binding=15)
        hobby: str = inject_field(binding="Skateboarding")

    return Adult, Child


adult_before_refactor, child_before_refactor = before_refactor()
adult_after_refactor, child_after_refactor = after_refactor()

registry = Registry()

adult_1 = registry[adult_before_refactor]
adult_2 = registry[adult_after_refactor]

assert adult_1.age == adult_2.age
assert adult_1.name == adult_2.name

print("Adults are the same!")

child_1 = registry[child_before_refactor]
child_2 = registry[child_after_refactor]

assert child_1.age == child_2.age
assert child_1.hobby == child_2.hobby

print("Children are the same!")
