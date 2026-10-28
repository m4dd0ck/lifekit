"""Exceptions raised by Lifekit's own code.

The CLI catches ``LifekitError`` and prints its message; anything else is a bug and keeps
its traceback.
"""


class LifekitError(Exception):
    """Base class for every error Lifekit raises on purpose."""


class InvalidValueError(LifekitError):
    """A value failed validation at the store boundary."""


class NotFoundError(LifekitError):
    """No live habit or goal has the given name."""


class AmbiguousNameError(LifekitError):
    """More than one live habit or goal has the given name."""


class DuplicateNameError(LifekitError):
    """A live habit or goal with that name already exists."""
