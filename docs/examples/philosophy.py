import minject


@minject.define
class Engine:
    cylinders: int = minject.field(binding=4)


@minject.define
class Car:
    engine: Engine = minject.field(binding=minject.inject.reference(Engine))


if __name__ == "__main__":
    registry = minject.Registry()
    car = registry[Car]
    assert isinstance(car, Car), "registry[Car] returns an object"
    assert isinstance(car.engine, Engine), "engine is injected into Car"
    assert car.engine.cylinders == 4, "engine uses the default cylinder count"

    registry_alt = minject.Registry()
    registry_alt[Engine] = Engine(cylinders=2)
    car_alt = registry_alt[Car]
    assert car_alt.engine.cylinders == 2, "cylinders can change w/ injection"

    print("philosophy example tests passed!")
