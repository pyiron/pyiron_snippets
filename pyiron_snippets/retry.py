from __future__ import annotations

import time
import warnings
from itertools import count
from typing import Callable, Optional, Tuple, Type, TypeVar, Union

T = TypeVar("T")


def retry(
    func: Callable[[], T],
    error: Union[Type[Exception], Tuple[Type[Exception], ...]],
    msg: str,
    at_most: Optional[int] = None,
    delay: float = 1.0,
    delay_factor: float = 1.0,
    log: bool | object = True,
) -> T:
    """
    Try to call `func` until it no longer raises `error`.

    Any other exception besides `error` is still raised.

    Args:
        func (callable): function to call, should take no arguments
        error (Exception or tuple thereof): any exceptions to be caught
        msg (str): messing to be written to the log if `error` occurs.
        at_most (int, optional): retry at most this many times, None means retry
                                forever
        delay (float): time to wait between retries in seconds
        delay_factor (float): multiply `delay` between retries by this factor
        logger (bool|object): Whether to pass a message to `warnings.warn` on each
            retry. (Default is True.) Optionally, an object with a :meth:`warn` method
            can be passed and the message will be sent there instead
            (e.g. `pyiron_snippets.logger.logger`).

    Raises:
        `error`: if `at_most` is exceeded the last error is re-raised
        Exception: any exception raised by `func` that does not match `error`

    Returns:
        object: whatever is returned by `func`
    """
    if at_most is None:
        tries = count()
    else:
        tries = range(at_most)
    for i in tries:
        try:
            return func()
        except error as e:
            warning = f"{msg} Trying again in {delay}s. Tried {i + 1} times so far..."
            if isinstance(log, bool):
                if log:
                    warnings.warn(warning)
            else:
                log.warn(warning)
            time.sleep(delay)
            delay *= delay_factor
            # e drops out of the namespace after the except clause ends, so
            # assign it here to a dummy variable so that we can re-raise it
            # in case the error persists
            err = e
    raise err from None
