"""Exceptions for NAD Serial."""


class NADBaseError(Exception):
    """Base class for NAD errors."""


class NADConnectionError(NADBaseError):
    """
    NAD Connection Error.

    When an error occurs while connecting to the device.
    """


class NADCommandError(NADBaseError, ValueError):
    """
    NAD Command Error.

    When a setting, operator or value is not supported by the device.
    """


class NADResponseError(NADBaseError, ValueError):
    """
    NAD Response Error.

    When a response is invalid.
    """


class NADTimeoutError(NADBaseError):
    """
    NAD Timeout Error.

    When the device does not respond to a command in time.
    """
