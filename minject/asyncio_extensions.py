"""
This module provides fallback implementations of asyncio features that
are not available in Python 3.7.
"""

try:
    from asyncio import to_thread
# This is copy pasted from here: https://github.com/python/cpython/blob/03775472cc69e150ced22dc30334a7a202fc0380/Lib/asyncio/threads.py#L1-L25
except ImportError:
    """High-level support for working with threads in asyncio"""

    import contextvars
    import functools
    from asyncio import events

    # Minject Specific Edit: I commented out the following line
    # and moved it out of the try - except block
    # __all__ = "to_thread",

    async def to_thread(func, /, *args, **kwargs):
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
