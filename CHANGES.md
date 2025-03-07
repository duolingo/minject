# Versioning

`minject` uses semantic versioning. To learn more about semantic versioning, see the [semantic versioning specification](https://semver.org/#semantic-versioning-200).

# Changelog

## v1.4.0

Allow `RegistryMetadata` to process bindings for unhashable objects. If a bound
object is unhashable, the binding key uses the object's ID instead.

## v1.3.0

Relax `RegistryInitConfig` from `Dict` to `Mapping`.

## v1.2.0

Remove workarounds for bugs and incompatibilities in Python 3.7 and 3.8.

## v1.1.2

Add missing dependency `packaging`.

Drop support for Python 3.7 and 3.8, which are at end-of-life.

## v1.1.1

Fix inject_define bindings for multiple class declarations with the same class
name in the same file ([#43](https://github.com/duolingo/minject/issues/43)).

## v1.1.0

Add support for async Python. This version introduces the following methods and decorators:

- `Registry.__aenter__`
- `Registry.__aexit__`
- `Registry.aget`
- `@async_context`

## v1.0.0

- Initial Release
