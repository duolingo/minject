# Dependency Injection

In this guide, you can learn about dependency injection and the `duoling_base.registry` module.

To see a working example of `duolingo_base.registry`, see the [Quick Start](#quick-start) section.

To learn what dependency injection is, and how you can use it in your projects,
see the [Fundamentals](#fundamentals) section.

# Quick Start

This section shows you how to create a script that
uses `duolingo_base.registry` to instantiate objects
through dependency injection.

## Set Up Your Environment

Create and activate a virtual environment by running the following commands in your terminal:

```console
python3 -m venv .pyenv
source .pyenv/bin/activate
```

Next, import `duolingo-base`:

```console
pip install --index-url https://pypi.duolingo.com/simple duolingo-base
```

Next, create a file named `serve.py`:

```console
touch serve.py
```

## Write Your Script

First, import the classes and modules you need to use dependency injection:

https://github.com/duolingo/python-duolingo-base/blob/0e6732d19897b766b482981ddca00336f05c32e0/docs/dependency_injection_examples/quick_start.py#L1-L2

Next, intialize an instance of the `Registry` class:

https://github.com/duolingo/python-duolingo-base/blob/0e6732d19897b766b482981ddca00336f05c32e0/docs/dependency_injection_examples/quick_start.py#L4-L5

Next, create your classes. Use the `inject.bind` function to specify how your `Registry`
instance should instantiate each of your classes:

https://github.com/duolingo/python-duolingo-base/blob/0e6732d19897b766b482981ddca00336f05c32e0/docs/dependency_injection_examples/quick_start.py#L7-L29

Use your `Registry` instance to instantiate your class:

https://github.com/duolingo/python-duolingo-base/blob/0e6732d19897b766b482981ddca00336f05c32e0/docs/dependency_injection_examples/quick_start.py#L32-L33

Call a method of your instantiated class:

https://github.com/duolingo/python-duolingo-base/blob/0e6732d19897b766b482981ddca00336f05c32e0/docs/dependency_injection_examples/quick_start.py#L35-L39

To view the entire script, click the link in any of the preceding code snippets.

# Fundamentals

In this section, you can learn what **dependency injection** is, and
how you can use it in your projects. Dependency injection is a software
engineering technique that allows a programmer to instantiate an object
without needing to provide arguments to the object's constructor.

To use the dependency injection technique, you must use a
**dependency injection framework**. A dependency injection framework
is a library that provides a mechanism that allows a programmer to instantiate
objects through dependency injection in a specific programming language or
technology stack.

At Duolingo, we use `duolingo_base.registry` as our dependency injection framework
when using Python.

# Understand the Value of Dependency Injection

Dependency injection is valuable for the following reasons:

- It allows you to instantiate objects without introducing dependencies
- It lets you ignore an object's constructor

## Example

The following example illustrates the value of dependency injection through code.

Say you have the following three classes in a module named `serve.py`:

```python
from db_helpers import DatabaseConfig, DatabaseUser
from serve_helpers import WebServerConfig, WebServerUser

class _Database:

    def __init__(self, DatabaseConfig, DatabaseUser):
        ...

class _WebServer:

    def __init__(self, WebServerConfig, WebServerUser)
        ...

class ApplicationManager:

    def __init__(self, _Database, _WebServer):
        ...
```

Without dependency injection, if you need to instantiate
`ApplicationManager` from a different Python module, you must import
all the dependencies of `ApplicationManager` into your other Python module
and instantiate the entire dependency tree:

<!-- untested pseudo-code -->

```python
from db_helpers import DatabaseConfig, DatabaseUser
from serve_helpers import WebServerConfig, WebServerUser
from serve import _Database, _WebServer, ApplicationManager

db_conf = DatabaseConfig(...)
db_user = DatabaseUser(...)
db = _Database(db_conf, db_user)
ws_conf = WebServerConfig(...)
ws_user = WebServerUser(...)
ws = _WebServer(ws_conf, ws_user)
app = ApplicationManager(db, we)
```

If you modified the preceding classes to use dependency injection, you could
instantiate `ApplicationManager` from another Python module without
needing to interact with the constructor. The following code shows
instantiating `ApplicationManager` through dependency injection:

<!-- untest pseudo-code -->

```python
from my_registry_instance import registry
from serve import ApplicationManager

app = registry[ApplicationManager]
```

# Use Dependency Injection

To use dependency injection through `duolingo_base.registry`, you must
perform the following actions:

1. Create a `Registry` instance
2. Provide **dependency resolution definitions** through `inject` functions
3. Use your dependency resolution definitions to instantiate
   objects with your `Registry` instance

A dependency resolution definition is a set of instructions that a
dependency resolution framework uses to instantiate a class. Dependency
resolution definitions must provide the following information:

- The class to instantiate
- Arguments for the class to instantiate's constructor

## Create a `Registry` instance

Use the `Registry` class to perform the following actions:

- Instantiate classes from dependency resolution definitions
- Store instantiated classes for reuse throughout your project

The following code snippet creates an instance of `Registry`:

<!-- untested -->

```python
registry = Registry()
```

## Define Dependency Resolution Definitions with `inject`

Use the functions `inject.bind` and `inject.define` to specify how dependencies resolve when you instantiate a class through dependency injection.

Use `inject.bind` when you need one instance of a class in your program.

Use `inject.define` when you need more than one instance of a class in your
program.

### Understand `inject.bind`

The function `inject.bind`, when used as a decorator on a class, adds
dependency resolution definitions as a
class attribute to the decorated class.

You must pass arguments to your class' constructor as keyword arguments to
`inject.bind`.

The following code shows how to use `inject.bind`:

https://github.com/duolingo/python-duolingo-base/blob/0e6732d19897b766b482981ddca00336f05c32e0/docs/dependency_injection_examples/inject_examples.py#L7-L21

### Understand `inject.define`

The function `inject.define` returns dependency resolution definitions
with which a `Registry` can instantiate a class.

The following code shows how to use `inject.define`:

https://github.com/duolingo/python-duolingo-base/blob/0e6732d19897b766b482981ddca00336f05c32e0/docs/dependency_injection_examples/inject_examples.py#L24-L36

## Understand `inject_define` and `inject_field`

Use the functions `inject_define` and `inject_field` to automatically generate an `__init__` method
for your class and specify dependency resolution definitions for the parameters of your `__init__`
method.

To see a code sample demonstrating how to use
`inject_define` and `inject_field`, see the
[Reduce Code Duplication](#reduce-code-duplication) section.

> **Note**
> The functions `inject_define` and `inject_field` are wrappers
> around the functions `attr.define` and `attr.field`.
> By default, `inject_define` disables all automatically generated code except `__init__`
> methods created by `attr.define`. You can configure how `attr.define` creates your decorated
> class with the `define_kwargs` keyword argument of `inject_define`.

### Reduce Code Duplication

Use `inject_define` and `inject_field` to reduce the code duplication that occurs
from using `inject.bind`. For example, let's say you want to specify the following dependency
resolution definitions for two classes, `Adult` and `Child`:

https://github.com/duolingo/python-duolingo-base/blob/b017ef5f8a39d722280c5eadd53ab00899b3ed28/docs/dependency_injection_examples/inject_define.py#L30-L40

Notice that you must reference the keyword argument to which the dependency resolution definitions correspond three times in each class:

- Once in the `inject.bind` decorator
- Once in the `__init__` method constructor
- Once in the `__init__` method body

You can refactor the preceding code with `inject_field` and `inject_define` to reduce
code duplication as follows:

https://github.com/duolingo/python-duolingo-base/blob/b017ef5f8a39d722280c5eadd53ab00899b3ed28/docs/dependency_injection_examples/inject_define.py#L46-L54

### Typing

`inject_define` and `inject_field` require a plugin to allow generated `__init__` methods
to be type checked by `mypy`.

To add the plugin to `mypy`, add the following code snippet to your
`mypy.ini` or `setup.cfg` file:

https://github.com/duolingo/python-duolingo-base/blob/b017ef5f8a39d722280c5eadd53ab00899b3ed28/docs/dependency_injection_examples/mypy.ini#L1-L2

## Instantiate Objects through Dependency Resolution with Your `Registry`

Once you have a class with dependency resolution definitions attached
through `inject.bind`, or dependency resolution definitions created through
`inject.define`, you can instantiate classes with your `Registry` instance.

To instantiate an object through an instance of the `Registry` class,
use dictionary lookup syntax:

```
registry = Registry()
instance = registry[MyClassWithDependencyResolutionDefined]
```

When you instantiate a class through a `Registry` instance,
the `Registry` uses the dependency resolution definitions present in the
dictionary lookup key to construct your instance.

The dependency resolution definitions contain a tree from which each argument
to the constructor of the class the `Registry` is instantiating can be
constructed. The root of the dependency resolution tree is the class you
wish to instantiate and the leaves are primitive types.

# Specify Recursive Dependency Resolution Definitions

If you need to construct the arguments or your class's constructor
through dependency resolution, you must specify a
**recursive dependency resolution definition**. A recursive dependency
resolution definition is a dependency resolution definition that references
the dependency resolution definitions of one or more other classes.

You can specify recursive dependency resolution definitions
with `inject.reference` and `inject.function`.

## Understand `inject.reference`

Use `inject.reference` when you need to reference the dependency resolution
definition of another class while constructing a dependency resolution
definition. `inject.reference` receives as an argument either a class that contains dependency resolution definitions added through
`inject.bind`, or dependency resolution definitions constructed through `inject.define`.

The following code snippet shows how to use `inject.reference`:

https://github.com/duolingo/python-duolingo-base/blob/0e6732d19897b766b482981ddca00336f05c32e0/docs/dependency_injection_examples/inject_examples.py#L39-L63

## Understand `inject.function`

Use `inject.function` when you need to apply
logic to dependency resolution definitions
while constructing a dependency resolution definition.

`inject.function` receives as arguments a callable followed by a set of
arguments which may or may not contain dependency resolution definitions.

The following code snippet shows how to use `inject.function`:

https://github.com/duolingo/python-duolingo-base/blob/0e6732d19897b766b482981ddca00336f05c32e0/docs/dependency_injection_examples/inject_examples.py#L66-L90

> **Note**
> A common use case of `inject.function` is parsing a configuration string into a
> type-safe object. To learn more about using configuration values with
> the `duolingo_base.registry` framework, see the
> [Use Config Parameters](#use-config-parameters) section.

# Storing Instantiated Classes

When you instantiate a class with the `duolingo_base.registry` framework,
the framework stores your instantiated class as the value in a key value
pair.

When you instantiate a class with dependency resolution
definitions attached to that class through `inject.bind`, use
that class' class object as the key to retrieve your instantiated class.
To view an example of retrieving a class with a class object key,
see the [Understand `inject.bind`](#understand-injectbind) section.

When you instantiate a class through dependency resolution definitions
created through `inject.define`, use the dependency resolution definitions
as the key to retrieve your instantiated class. To view an example of retrieving
a class through dependency resolution definitions, see the
[Understand `inject.define`](#understand-injectdefine)
section.

> **Note**
> On the first instantiation of your class, your `Registry` instance uses the
> dependency resolution definitions contained in the you passed to
> instantiate your class.

# Dependency Injection and Flask

In this section, you can learn how to use `duolingo_base.registry` with the `Flask` web framework.

## Use Config Parameters

To use parameters from the `YAML` files in your `config/` directory in
your dependency resolution definitions,
use the `inject.config` and `inject.nested_config` functions.

The `inject.config` function allows you to access a value in a `YAML` config file, and does not support [dot notation](https://developer.mozilla.org/en-US/docs/Learn/JavaScript/Objects/Basics#dot_notation)
for object traversal. The `inject.nested_config`
function allows you to access a value in a `YAML` config file, and does
support dot notation for object traversal.

For example lets, say your `config/prod.yml` file contains the following
snippet of `YAML` code:

```yaml
nested:
  value: i am nested

flat_value: i am flat
```

You can access the preceding values defined `config/prod.yml` in a
dependency resolution definition as follows:

<!-- untested -->

```python
inject.bind(
    flat_value = inject.config("flat_value")
    nested_value = inject.nested_config("nested.value")
)
class MyClass:
    ...
```

## Global Registry Instance

To access a `Registry` instance throughout your application, store an
intialized `Registry` instance in the `flask.current_app` object.

The following code snippet shows how to attach a `Registry` instance
to a `Flask` application:

<!-- Code snippets in this section are from previous documentation -->

```python
app = flask.application()
app.registry = registry.initialize()
```

The following code snippet shows how to retrieve the `Registry` instance
in the view layer of your application:

> **Warning**
> The following code snippet contains a bug related to thread safety.
> To learn what this bug is and how to fix it, see the [Thread Safety](#thread-safety)
> section of this guide.

```python
from flask import current_app

@app.route('/phrase')
def get_phrase(self):
    phrases = current_app.registry[PhraseList]
    return phrases.get_phrase(request.args['name'])
```

## Thread Safety

The `Registry` object is not thread safe, and you should not access
it in threaded sections of your code. This means that you should not
use the `Registry` to instantiate objects in a function decorated with
`@app.route`, or in any function called from a function decorated with
`@app.route`.

> **Important**
> Ensure you resolve all dependency resolution definitions with your
> `Registry` instance at application startup. Your `Registry` instance
> resolves a dependency resolution definition the first time you perform
> a dictionary lookup with the key containing that dependency
> resolution on your `Registry` instance.

To use a `Registry` instance in a `Flask` route, use **class-based views**.
Class-based views are a feature of the `duolingo_base` library that allow
you to add state to your route handlers.

The following code-snippet shows how to use an object constructed through a
`Registry` instance within a `Flask` route in a thread safe manner:

<!-- Untested code snippet -->

```python
from flask import current_app
from application import MyClass
from duolingo_base.view import FlaskView, View

@inject.bind(
    argument = "dependencies shmapendencies"
)
class MyView(FlaskView):
    def __init__(self, argument) -> None:
        super().__init__()
        self.class_instance = current_app.registry[MyClass]
        self.argument = argument

    @View.route("/message", methods=["GET"])
    def get_message(self) -> str:
        return f"{self.class_instance.message} {self.argument}!"
```

# Testing Dependency Injection enabled Code

You can test code that uses `duolingo_base.registry` exactly as
you would test code that does not use `duolingo_base.registry`.
This is because no features of `duolingo_base.registry` change
the API or behavior of classes in your code.

For example, say you use the following class in your application:

https://github.com/duolingo/python-duolingo-base/blob/0e6732d19897b766b482981ddca00336f05c32e0/docs/dependency_injection_examples/class_for_test.py#L7-L19

You can test this class with the `pytest` like this:

https://github.com/duolingo/python-duolingo-base/blob/0e6732d19897b766b482981ddca00336f05c32e0/docs/dependency_injection_examples/test.py#L4-L7

## Instantiate Mock Objects `duolingo_base.registry`

To instantiate an instance of a class with mock constructor arguments
specified by your dependency resolution definitions, use the `mock` function.

For example, say you have the following classes in your application:

https://github.com/duolingo/python-duolingo-base/blob/f0959952d659f0dc033babb73224f03b43df24c9/docs/dependency_injection_examples/mock_examples.py#L1-L23

To instantiate an instance of the `Child` class with mock constructor arguments
corresponding to your dependency resolution definitions, use the `mock`
function as follows:

https://github.com/duolingo/python-duolingo-base/blob/f0959952d659f0dc033babb73224f03b43df24c9/docs/dependency_injection_examples/mock_examples.py#L25-L31

If you would like to instantiate your class with mocks other than
`MagicMock`, pass a mocking function. A mocking function is a
function that takes a binding to your function as an argument and
returns your desired mock object.

The following code snippet shows how to pass a mocking function to the
`mock` function:

https://github.com/duolingo/python-duolingo-base/blob/f0959952d659f0dc033babb73224f03b43df24c9/docs/dependency_injection_examples/mock_examples.py#L39-L49