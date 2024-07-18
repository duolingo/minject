"""Test the service annotation interface"""

import unittest

import minject


class TestServiceInterface(unittest.TestCase):
    def test_simple(self):
        @minject.service
        class Engine:
            cylinders: int = 4

        @minject.service
        class Car:
            engine: Engine = minject.reference(Engine)

        registry = minject.Registry()
        car = registry[Car]

        assert isinstance(car, Car), "registry[Car] returns an object"
        assert isinstance(car.engine, Engine), "engine is injected into Car"
        assert car.engine.cylinders == 4, "engine uses the default cylinder count"


if __name__ == "__main__":
    unittest.main()
