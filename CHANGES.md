# Versioning

`minject` uses semantic versioning. To learn more about semantic versioning, see the [semantic versioning specification](https://semver.org/#semantic-versioning-200).

# Changelog

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
