from functools import partial

from mypy.plugin import Plugin
from mypy.plugins import attrs
from packaging import version

_INJECT_DEFINE_FUNC = "inject_define"


class RegistryMypyPlugin(Plugin):
    """
    This plugin exists to allow mypy to recognize the inject_define decorator
    as identical to attr.define. Mypy will not apply it's attrs plugin unless
    these two hooks are called.

    I do not fully understand what these hooks do. This is just copying
    these sections of the mypy source code:

    decorator 1: https://github.com/python/mypy/blob/a6bd80ed8c91138ce6112b5ce71fc406d426cd01/mypy/plugins/default.py#L132-L138
    decorator 2: https://github.com/python/mypy/blob/a6bd80ed8c91138ce6112b5ce71fc406d426cd01/mypy/plugins/default.py#L159-L162
    """

    def get_class_decorator_hook(self, fullname: str):
        if _INJECT_DEFINE_FUNC in fullname:
            return attrs.attr_tag_callback
        return None

    def get_class_decorator_hook_2(self, fullname: str):
        if _INJECT_DEFINE_FUNC in fullname:
            # slots default added in mypy version 1.5
            return partial(
                attrs.attr_class_maker_callback, auto_attribs_default=None, slots_default=True
            )
        return None


class RegistryMypyPluginLegacy(Plugin):
    def get_class_decorator_hook(self, fullname: str):
        if _INJECT_DEFINE_FUNC in fullname:
            return attrs.attr_tag_callback
        return None

    def get_class_decorator_hook_2(self, fullname: str):
        if _INJECT_DEFINE_FUNC in fullname:
            return partial(attrs.attr_class_maker_callback, auto_attribs_default=None)
        return None


def plugin(mypy_version: str):
    too_old_version = version.parse(mypy_version) < version.parse("0.6.0")

    if too_old_version:
        raise ValueError(
            "mypy version must be at least 0.6.0 to use the registry plugin."
            f"You are using version {mypy_version}"
        )

    use_legacy = version.parse(mypy_version) < version.parse("1.5.0")

    if use_legacy:
        return RegistryMypyPluginLegacy

    return RegistryMypyPlugin
