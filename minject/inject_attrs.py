import inspect
from collections import defaultdict
from platform import python_version
from typing import Any, DefaultDict, Dict, List, Optional, Type, TypeVar

from attr import define, field
from packaging import version

from minject import inject

_T = TypeVar("_T")
_P = TypeVar("_P")

_DEPTH_OF_INJECT_FIELD_CALLER = 3
_DEPTH_OF_INJECT_DEFINE_CALLER = 3
_DEPTH_OF_INJECT_DEFINE_CALLER_IF_NO_ARGS = 2
_DEPTH_OF_VAR_TO_WHICH_BINDING_IS_ASSIGNED = 2

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


def _get_calling_function_name(depth: int) -> str:
    return inspect.stack()[depth].function


def _get_calling_function_file(depth: int) -> str:
    return inspect.stack()[depth].filename


def _build_key(func_name: str, func_file: str) -> str:
    return f"__{func_name}__{func_file}__"


def _get_calling_function_key_from_depth(depth: int) -> str:
    func_name = _get_calling_function_name(depth=depth)
    func_file = _get_calling_function_file(depth=depth)
    return _build_key(func_name=func_name, func_file=func_file)


def _get_calling_function_key_from_filename_and_key(func_name: str, func_file: str) -> str:
    return _build_key(func_name=func_name, func_file=func_file)


_key_binding_mapping: DefaultDict[str, dict] = defaultdict(lambda: {})


def _get_init_kwarg_assignment() -> str:
    """
    get the name of the variable that will be assigned the return
    value of the function that calls this function.
    """
    frame = inspect.currentframe()
    outer_frame = inspect.getouterframes(frame)[_DEPTH_OF_VAR_TO_WHICH_BINDING_IS_ASSIGNED]
    optional_code_context = inspect.getframeinfo(outer_frame[0]).code_context
    if not optional_code_context:
        raise ValueError(
            "Could not find the variable to which the binding is assigned. Are you calling inject_field properly?"
        )
    code_string = optional_code_context[0].strip()
    var_and_type = code_string.split("=")[0].rstrip().lstrip()
    var = var_and_type.split(":")[0].rstrip().lstrip()
    return var


def inject_field(binding=_T, **attr_field_kwargs) -> Any:
    """
    Wrapper around attr.field which takes an argument to specify registry
    bindings
    """
    # add the binding to the key_binding_mapping to be retrieved in the call
    # to inject_define
    var_name = _get_init_kwarg_assignment()
    _key_binding_mapping[_get_calling_function_key_from_depth(_DEPTH_OF_INJECT_FIELD_CALLER)][
        var_name
    ] = binding
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

    # this variable represent how deep to look on the call stack
    # to determine the name of the function that called this function.
    # this is different depending on how a user used the decorator (with or without kwargs)
    depth_of_caller = _DEPTH_OF_INJECT_DEFINE_CALLER

    def inject_define_inner(cls: Type[_P]) -> Type[_P]:
        # apply attr.define to generate static methods
        cls = define(cls, **attrs_kwargs)

        # get binding to apply to the class
        file_of_class_being_bound = _get_calling_function_file(depth_of_caller)
        key = _get_calling_function_key_from_filename_and_key(
            cls.__name__, file_of_class_being_bound
        )
        bindings = _key_binding_mapping[key]

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
        depth_of_caller = _DEPTH_OF_INJECT_DEFINE_CALLER_IF_NO_ARGS
        return inject_define_inner

    return inject_define_inner(maybe_cls)
