# minject

## Philosophy

`minject` is a dependency injection tool that aims to be easy to use, easy to understand, and easy to ignore. To
accomplish this we follow these principles:

- **Minimize boilerplate**: Adding dependency injection to a class should
  require as little extra code as possible. You can add or change a dependency
  with only one line of code.
- **Be obvious**: We keep the dependency injection pieces close to the code, not
  separated into a different file. You should be able to understand where
  and how `minject` is working from looking at the source code.
- **Work as plain Python**: Dependency injection must be easy to ignore. You can
  always use `minject` classes as if they were regular classes.

Here's an [example](docs/examples/philosophy.py) to demonstrate:

```python
import minject

@minject.define
class Engine:
    cylinders: int = minject.field(binding=4)

@minject.define
class Car:
    engine: Engine = minject.field(binding=minject.inject.reference(Engine))
```


This code follows the preceding principles in the following ways:

- There isn't much boilerplate: one call to `@minject.define` to mark a class for
injection, and one `minject.field()` to annotate what it depends on.
- These annotations clearly show `minject` is involved and provide a starting
point for learning more.
- If you need to use this class without `minject`
you can call `my_car = Car(my_engine)` and it will work how you'd
expect without any hidden magic.
