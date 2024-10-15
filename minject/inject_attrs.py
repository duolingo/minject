import inspect
from collections import defaultdict
from dataclasses import dataclass
from platform import python_version
from typing import Any, DefaultDict, Dict, List, Optional, Type, TypeVar

from attr import define, field
from packaging import version

from minject import inject

_T = TypeVar("_T")
_P = TypeVar("_P")

_INJECT_DEFINE_DEFINE_KWARGS_DEFAULT_VAL: Dict[str, Any] = {}


class _AttrDefineKwarg:
    """
    Class to hold kwargs for attr.define. Includes what version
    a value was added as a paramter to attr.define. This is used
    to disable features not tied to generating __init__ methods.
    """

    def __init__(
        self,
        key_word: str,
        attr_version_start: str,
        attr_verson_end: Optional[str] = None,
        value: bool = False,
    ) -> None:
        self.key_word: str = key_word
        self.attr_version_start: str = attr_version_start
        self.attr_version_end: Optional[str] = attr_verson_end
        self.value: bool = value


# this list disables more settings that are enabled
# by default in an attempt to disable settings that were previously
# enabled by default but no longer are, like eq.
_ATTRS_DEFINE_DISABLE_EVERYTHING_BUT_INIT: List[_AttrDefineKwarg] = [
    _AttrDefineKwarg("init", "0.0.0", value=True),
    _AttrDefineKwarg("repr", "0.0.0"),
    _AttrDefineKwarg("hash", "0.0.0"),
    _AttrDefineKwarg("str", "0.0.0"),
    _AttrDefineKwarg("slots", "16.0.0"),
    _AttrDefineKwarg("frozen", "16.1.0"),
    _AttrDefineKwarg("weakref_slot", "18.2.0"),
    _AttrDefineKwarg("auto_exc", "19.1.0"),
    _AttrDefineKwarg("eq", "19.2.0"),
    _AttrDefineKwarg("order", "19.2.0"),
    _AttrDefineKwarg("cmp", "19.2.0", "21.1.0"),
    _AttrDefineKwarg("auto_detect", "20.1.0"),
    _AttrDefineKwarg("match_args", "21.3.0"),
]


def _get_compatible_attrs_define_kwargs() -> Dict[str, bool]:
    """
    get kwargs compatible with current running version of attrs
    """
    # if you are running python 3.8 or greater, use importlib.metadata
    # to get the version of attrs. Otherwise, use the __version__ attribute
    if version.parse(python_version()) >= version.parse("3.8.0"):
        from importlib.metadata import version as importlib_version  # type: ignore

        attr_version = importlib_version("attrs")
    else:
        # this is deprecated, but we still support python 3.7
        from attr import __version__ as _attr_version

        attr_version = _attr_version

    parsed_attr_version = version.parse(attr_version)
    attrs_define_kwargs: Dict[str, bool] = {}
    for kwarg in _ATTRS_DEFINE_DISABLE_EVERYTHING_BUT_INIT:
        if version.parse(kwarg.attr_version_start) > parsed_attr_version:
            continue
        if (
            kwarg.attr_version_end is not None
            and version.parse(kwarg.attr_version_end) < parsed_attr_version
        ):
            continue
        attrs_define_kwargs[kwarg.key_word] = kwarg.value
    return attrs_define_kwargs


@dataclass(frozen=True)
class _BindingKey:
    __slots__ = ("filename", "class_lineno")
    filename: str
    class_lineno: int  # The line containing the "class" keyword.


_key_binding_mapping: DefaultDict[_BindingKey, dict] = defaultdict(lambda: {})


def inject_field(binding=_T, **attr_field_kwargs) -> Any:
    """
    Wrapper around attr.field which takes an argument to specify registry
    bindings
    """
    stack = inspect.stack()
    # The first frame of the stack is the call to inject_field itself.

    # We assume that inject_field is called directly (not via some kind of
    # wrapper), so the second frame of the stack should be the field
    # declaration. Extract the name of the field.
    field_frame = stack[1]
    name = ""
    if len(field_frame.code_context) > 0:
        code = field_frame.code_context[0].strip()
        name_and_type = code.split("=", maxsplit=1)[0].rstrip().lstrip()
        name = name_and_type.split(":", maxsplit=1)[0].rstrip().lstrip()
    if not name:
        raise ValueError(
            "Could not find the variable to which the binding is assigned. Are you calling inject_field properly?"
        )

    # The third frame of the stack should be the class declaration (containing
    # the "class" keyword). We use that line number as the key for looking up
    # bindings, so double-check that that assumption holds.
    # (If not, our inferred field name is probably wrong too!)
    class_frame = stack[2]
    if len(class_frame.code_context) < 1 or not class_frame.code_context[0].strip().startswith(
        "class "
    ):
        raise ValueError(
            "Could not find line containing class declaration. Are you calling inject_field properly?"
        )

    key = _BindingKey(filename=class_frame.filename, class_lineno=class_frame.lineno)
    _key_binding_mapping[key][name] = binding
    return field(**attr_field_kwargs)


def inject_define(
    maybe_cls: Optional[Type[_T]] = None,
    define_kwargs: Dict[str, Any] = _INJECT_DEFINE_DEFINE_KWARGS_DEFAULT_VAL,
):
    # use default attrs kwargs or user supplied attrs kwargs
    attrs_kwargs: Dict[str, Any] = {}
    if define_kwargs is not _INJECT_DEFINE_DEFINE_KWARGS_DEFAULT_VAL:
        attrs_kwargs = define_kwargs
    else:
        attrs_kwargs = _get_compatible_attrs_define_kwargs()

    def inject_define_inner(cls: Type[_P]) -> Type[_P]:
        # Identify the line containing the "class" keyword for cls: that is
        # the line number that we used in the binding key for its fields.
        class_lineno = None
        (lines, start_lineno) = inspect.getsourcelines(cls)
        for lineno, line in enumerate(lines, start_lineno):
            if line.strip().startswith("class "):
                class_lineno = lineno
        if class_lineno is None:
            raise ValueError(
                "Could not find line containing class declaration. Are you calling inject_define properly?"
            )

        # get bindings to apply to the class
        key = _BindingKey(
            filename=inspect.getsourcefile(cls),
            class_lineno=class_lineno,
        )
        bindings = _key_binding_mapping[key]
        del _key_binding_mapping[key]

        # apply attr.define to generate static methods
        cls = define(cls, **attrs_kwargs)

        # apply the bindings to the class
        init_signature = inspect.signature(cls.__init__)
        init_signature_kwargs = list(init_signature.parameters.keys())
        kwargs = {
            arg_name: bindings.get(arg_name)
            for arg_name in init_signature_kwargs
            if bindings.get(arg_name) is not None
        }
        inject.bind(**kwargs)(cls)

        return cls

    if maybe_cls is None:
        return inject_define_inner

    return inject_define_inner(maybe_cls)
