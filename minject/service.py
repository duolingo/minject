# The @minject.service annotation adds dependency injection details to a class.

# based heavily on the dataclasses.py module in the Python standard library
# https://github.com/python/cpython/blob/v3.11.9/Lib/dataclasses.py

from .metadata import _gen_meta


# A sentinel object to detect if a parameter is supplied or not.  Use
# a class to give it a better repr.
class _MISSING_TYPE:
    pass


MISSING = _MISSING_TYPE()


# The name of an attribute on the class where we store the Field objects.
_FIELDS = "__minject_fields__"


# Instances of Field are only ever created from within this module,
# and only from the field() function, although Field instances are
# exposed externally as (conceptually) read-only objects.
#
# name and type are filled in after the fact, not in __init__.
# They're not known at the time this class is instantiated, but it's
# convenient if they're available later.
#
# When cls._FIELDS is filled in with a list of Field objects, the name
# and type fields will have been populated.
class Field:
    __slots__ = ("name", "type", "binding")

    def __init__(self, binding):
        self.name = None
        self.type = None
        self.binding = binding

    def __repr__(self):
        return "Field(" f"name={self.name!r},type={self.type!r},binding={self.binding!r}," ")"


# This function is used instead of exposing Field creation directly,
# so that a type checker can be told (via overloads) that this is a
# function whose type depends on its parameters.
def field(*, binding):
    """Return an object to identify dataclass fields."""
    return Field(binding)


def _get_field(cls, a_name, a_type):
    # Return a Field object for this field name and type.

    # If the default value isn't derived from Field, then it's only a
    # normal default value.  Convert it to a Field().
    default = getattr(cls, a_name, MISSING)
    if isinstance(default, Field):
        f = default
    else:
        f = field(binding=default)

    # Only at this point do we know the name and the type.  Set them.
    f.name = a_name
    f.type = a_type

    return f


def _init_fn(fields):
    def service_init(self, **kwargs):
        # Set attributes based on the fields.
        for f in fields:
            setattr(self, f.name, kwargs[f.name])

    return service_init


def _process_class(cls):
    fields = {}

    # TODO: support parameters?
    # https://github.com/python/cpython/blob/v3.11.9/Lib/dataclasses.py#L902-L903

    # TODO: support base classes?
    # https://github.com/python/cpython/blob/v3.11.9/Lib/dataclasses.py#L905-L920

    # Annotations that are defined in this class (not in base
    # classes).  If __annotations__ isn't present, then this class
    # adds no new annotations.  We use this to compute fields that are
    # added by this class.
    #
    # Fields are found from cls_annotations, which is guaranteed to be
    # ordered.  Default values are from class attributes, if a field
    # has a default.  If the default value is a Field(), then it
    # contains additional info beyond (and possibly including) the
    # actual default value.  Pseudo-fields ClassVars and InitVars are
    # included, despite the fact that they're not real fields.  That's
    # dealt with later.
    cls_annotations = cls.__dict__.get("__annotations__", {})

    # Now find fields in our class.  While doing so, validate some
    # things, and set the default values (as class attributes) where
    # we can.
    cls_fields = []
    for name, type in cls_annotations.items():
        cls_fields.append(_get_field(cls, name, type))

    for f in cls_fields:
        fields[f.name] = f

        # If the class attribute (which is the default value for this
        # field) exists and is of type 'Field', replace it with the
        # real default.  This is so that normal class introspection
        # sees a real default value, not a Field.
        if isinstance(getattr(cls, f.name, None), Field):
            # If there's no default, delete the class attribute.
            # This happens if we specify field(repr=False), for
            # example (that is, we specified a field object, but
            # no default value).  Also if we're using a default
            # factory.  The class attribute should not be set at
            # all in the post-processed class.
            delattr(cls, f.name)

    if "__init__" not in cls.__dict__:
        cls.__init__ = _init_fn(cls_fields)

    meta = _gen_meta(cls)
    meta.update_bindings(**{f.name: f.binding for f in fields.values()})

    return cls


def service(cls=None):
    """Create minject metadata based on the fields defined in the class.

    Examines PEP 526 __annotations__ to determine fields.

    Based on [dataclasses](https://docs.python.org/3/library/dataclasses.html).
    """

    def wrap(cls):
        return _process_class(cls)

    # See if we're being called as @service or @service().
    if cls is None:
        # We're called with parens.
        return wrap

    # We're called as @service without parens.
    return wrap(cls)
