Dependency Injection
====================


What is Dependency Injection?
-----------------------------

[Dependency Injection](https://en.wikipedia.org/wiki/Dependency_injection)
is "a software design pattern that implements inversion of control for
resolving dependencies." Essentially it is a way of initializing classes and
connecting them to each other via references. It helps to avoid singletons
and facilitate unit testing.

The Spring Framework in Java in an example of a popular dependency injection
framework.


Why should I use it?
--------------------

If you have an object oriented design, it can be difficult to initialize all
of the long-lived objects in your program, especially when they contain complex
nested dependencies, or are referenced from many different contexts. In Python
web frameworks this can be especially problematic because handling of routes is
often done with simple functions that are scattered across several modules.
The common way of dealing with this is by creating global singletons that are
used everywhere, but this can make configuration and unit testing difficult.
Below is an example of a program that uses this strategy:

```python
class MyComplexThingManager(object):
    def __init__(thing_loader, thing_cache):
        self._loader = thing_loader
        self._cache = thing_cache

        self._prefill_cache()

    def calculate_thing(user, action):
        thing = self._loader.get_for(user_id)
        thing.change(action)
        self._cache.update(thing)
        return thing

THING_INSTANCE = MyComplexThingManager(THING_LOADER_INSTANCE,
                                       THING_CACHE_INSTANCE)

@app.route('/thing')
def get_thing(self):
    user_id = request.args['user_id']
    action = request.args['action']

    thing = THING_INSTANCE.calculate_thing(user_id, action)

    return render_template('thing.html', thing)
```

The problem with this approach is the global singleton instances. Any module
that imports the module containing the global singleton will create a new
instance of the class automatically, and in this case perform an expensive
cache fill operation. This will happen for unit tests, scripts and any other
piece of code that unsuspectingly imports that module (or any other module that
imports it in turn). To avoid the global singleton that initializes
automatically, one could write an `init_thing()` function which instantiates
these classes. Unfortunately, the web service now requires some sort of
global initialize routine which imports and calls all of those `init_thing()`
functions.

Another issue adding complexity is the references to the loader and
the cache (the "dependencies"). In order to initialize the manager you
need to know how to construct the loader and the cache, and perhaps the loader
and the cache have their own dependencies, and those further have their own.
This can result in long chains of constructor calls that need to be changed
whenever any of the downstream classes change. Additionally, it can be
difficult to configure these classes in different environments.


How does this library handle Dependency Injection?
--------------------------------------------------

This library contains a "Registry" module (duolingo.base.util.registry). Once
a `Registry` instance is created, it can be used to initialize objects and
provide references to dependency objects, while making it easy to configure
and customize those objects based on the environment. This `Registry` object
can be a singleton if needed; in Flask, a great place to store it in is the
`flask.current_app` object, which is available in any request handler. You can
then treat the `Registry` object like a dictionary to get out a class.

```python
app = flask.application()
app.registry = registry.initialize()

class PhraseList(object):
    def get_phrase(self, name):
        return random.choice(['Hello %s', 'Goodbye %s']) % name

@app.route('/phrase')
def get_phrase(self):
    phrases = current_app.registry[PhraseList]
    return phrases.get_phrase(request.args['name'])
```

The registry will return an initialized instance of PhraseList which you can
use. The registry will store this instance and return it on future calls.

If you have a class that needs init arguments, you can tell the registry what
values to use with the annotation system.

```python
@registry.bind(phrases=['How are you, %s?', 'So long %s'])
class PhraseList(object):
    def __init__(self, phrases):
        self._phrases = phrases

    def get_phrase(self, name):
        return random.choice(self._phrases) % name
```

One reason this could be useful is if you want to try different phrases in
testing, you could then create an instance with another value. This really
becomes powerful when combined with the `registry.reference` function.

```python
@registry.bind(url='http://localhost/my_phrases.txt')
def PhraseLoader(object):
    def __init__(self, url):
        self._url = url

    def load_phrases(self, url):
        ...


@registry.bind(loader=registry.reference(PhraseLoader),
               category='greetings')
def PhraseBuilder(object):
    def __init__(self, loader, category):
        self._loader = loader
        self._category = category

    def get_phrase(self, name):
        phrases = self._loader.load_phrases(self._category)
        return random.choice(phrases) % name
```

Now you can have a chain of objects that depend on each other; perhaps the
loader uses a `PhraseCache` to cache results that it gets from a `PhraseApi`.
The `PhraseApi` may in turn share the same instance of `ApiClient` with the
hypothetical `UserApi` and `HistoryApi`, each in separate modules.

In addition to `bind`, there is a `define` function which is useful when you
don't need to write any new code in a new class, but just want to
instantiate a generic class that already exists. (You can also use this
capability to pass init arguments to the reference function.)
Let's say we already have a class called `GenericCache` that handles caching
objects, and a `GenericLoader` which will fallback to an api call if the
object is missing from the cache.

```python
PhraseLoader = registry.define(GenericLoader,
    api=registry.reference(PhraseApi),
    cache=registry.reference(GenericCache, name="phrase", expire=60),
)

loader = registry[PhraseLoader]
```

The `loader` variable will now reference an instance of the `GenericLoader`
type that was initialized using the provided api and cache arguments.
Additionally, the cache argument will be a `GenericCache` initialized with the
provided name and expiration time.
