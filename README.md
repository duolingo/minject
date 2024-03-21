# minject

## Philosophy

Minject aims to be lightweight - easy to use, easy to understand, and easy to
ignore. We follow a few guiding principles to accomplish this:

- **Minimize boilerplate**: Adding dependency injection to a class should
  require as little extra code as possible. Adding or changing a dependency of
  a class should ideally only take one line. Make the common use case
  simple.
- **Be obvious**: Keep the dependency injection pieces close to the code it
  works on. Don't separate it into a different file that's hard to discover
  Someone who's never seen Minject annotations before should immediately know
  that a class is using it and be able to figure out how. It should be easy to
  understand what Minject is doing and why.
- **Work as plain Python**: It should be easy to ignore dependency injection
  entirely and treat Minject classes as if they were regular Python objects.
  This is also useful for writing unit tests without needing complex changes
  to injection behavior. Using a class in another context such as a script
  shouldn't automatically trigger a bunch of injection magic.

Here's a simplified example to demonstrate:

```
@minject.define
class Foo:
    bar = minject.field(Bar)
```

There isn't much boilerplate: one call to `@minject.define` to mark a class for
injection, and one `minject.field()` to annotate what it depends on. Likewise,
these annotations clearly show Minject is involved and provide a starting point
for learning more. Finally, if need to use this class without Minject you can
simply call `foo = Foo(some_bar)` and it will work how you'd expect without any
hidden magic.
