"""
This module provides fallback implementations of asyncio features that
are not available in Python 3.7.
"""

import asyncio

if hasattr(asyncio, "to_thread"):
    from asyncio import to_thread
# This is copy pasted from here: https://github.com/python/cpython/blob/03775472cc69e150ced22dc30334a7a202fc0380/Lib/asyncio/threads.py#L1-L25
else:
    """High-level support for working with threads in asyncio"""

    import contextvars
    import functools
    from asyncio import events

    # Minject Specific Edit: I commented out the following line
    # and moved it out of the try - except block
    # __all__ = "to_thread",

    # Minject Specific Edit: I removed the '/' from the function signature,
    # as this is not supported in python 3.7 (added in python 3.8).
    # The '/' forces that "func" be passed positionally (I.E. first argument
    # to to_thread). Users of this extension must be careful to pass the argument
    # to "func" positionally, or there could be different behavior
    # when using minject in python 3.7 and python 3.9+. I added a "type: ignore"
    # comment to silence mypy errors related to defining a function with a
    # different signature.
    # original asyncio source: "async def to_thread(func, /, *args, **kwargs):"
    async def to_thread(func, *args, **kwargs):  # type: ignore
        """Asynchronously run function *func* in a separate thread.

        Any *args and **kwargs supplied for this function are directly passed
        to *func*. Also, the current :class:`contextvars.Context` is propagated,
        allowing context variables from the main thread to be accessed in the
        separate thread.

        Return a coroutine that can be awaited to get the eventual result of *func*.
        """
        loop = events.get_running_loop()
        ctx = contextvars.copy_context()
        func_call = functools.partial(ctx.run, func, *args, **kwargs)
        return await loop.run_in_executor(None, func_call)


__all__ = "to_thread"
