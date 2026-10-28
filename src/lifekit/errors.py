"""Exceptions raised by Lifekit's own code.

The CLI catches ``LifekitError`` and prints its message; anything else is a bug and keeps
its traceback.
"""


class LifekitError(Exception):
    """Base class for every error Lifekit raises on purpose."""


class InvalidValueError(LifekitError):
    """A value failed validation at the store boundary."""
