"""Helpers for NAD Serial."""

import logging
import math
import re
from typing import Any

from .exceptions import NADCommandError

ValueType = str | int | float | bool
REPORT_MESSAGE = "Please report this to the NAD Serial library maintainers on https://github.com/rrooggiieerr/nad_serial.py/issues"

SETTING_RE = re.compile(r"[A-Za-z0-9]+(\.[A-Za-z0-9]+)+")

logger = logging.getLogger(__name__)


def parse_response(response: bytes) -> tuple[str | None, str | None]:
    """Split a NAD device response into the raw setting name and value."""
    if not response:
        return None, None

    response = response.strip(b" \t\r\n\x00")
    response_str = response.decode("ascii", errors="replace")
    try:
        setting, value = response_str.split("=", 1)
        return setting.strip(), value.strip()
    except ValueError:
        return None, None


def parse_value(setting: str, value: str, config: dict[str, Any]) -> ValueType | None:
    """Convert a raw NAD device value using the setting's config."""
    if config["type"] in ["boolean", "enum"] and value not in config["values"]:
        logger.warning(
            "%s returned an unsupported value %s. %s", setting, value, REPORT_MESSAGE
        )

    if config["type"] == "number":
        if value in ["None", "Unknown"]:
            return None
        try:
            return int(value)
        except ValueError:
            try:
                return float(value)
            except ValueError:
                logger.warning(
                    "%s returned an invalid number %s. %s",
                    setting,
                    value,
                    REPORT_MESSAGE,
                )
                return None
    if config["type"] == "boolean":
        if value in config["values"]:
            return bool(config["values"].index(value))
        return None

    return value


def build_command(
    setting: str,
    operator: str,
    value: ValueType | None = None,
    config: dict[str, Any] | None = None,
) -> str:
    """Builds a command for the NAD device."""
    if not SETTING_RE.fullmatch(setting):
        raise NADCommandError(f"Invalid characters in setting {setting!r}")
    if isinstance(value, str) and not (value.isascii() and value.isprintable()):
        raise NADCommandError(f"Invalid characters in value {value!r}")
    if operator not in ("=", "+", "-", "?"):
        raise NADCommandError(f"Invalid operator {operator}")
    if config is not None and operator not in config["operators"]:
        raise NADCommandError(f"Unsupported operator {operator} for {setting}")
    if value is not None and operator != "=":
        raise NADCommandError(f"Invalid operator {operator} to set value")
    if value is None and operator == "=":
        raise NADCommandError("Missing value")

    command = f"{setting}{operator}"

    if value is not None:
        if not isinstance(config, dict):
            raise NADCommandError(f"No configuration for {setting}")
        if config["type"] == "string":
            if not isinstance(value, str):
                raise NADCommandError(
                    f"Invalid value {value} for {setting}, not a string"
                )
            if "regex" in config and not re.fullmatch(config["regex"], value):
                raise NADCommandError(f"Invalid value format {value} for {setting}")
        if config["type"] == "number":
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise NADCommandError(
                    f"Invalid value {value} for {setting}, not a number"
                )
            if not math.isfinite(value):
                raise NADCommandError(
                    f"Invalid value {value} for {setting}, not a valid number"
                )
            if "min" in config and value < config["min"]:
                raise NADCommandError(
                    f"Value {value} for {setting} is below the minimum {config['min']}"
                )
            if "max" in config and value > config["max"]:
                raise NADCommandError(
                    f"Value {value} for {setting} is above the maximum {config['max']}"
                )
        if config["type"] == "boolean" and not isinstance(value, (bool, str)):
            raise NADCommandError(f"Invalid value {value} for {setting}")
        if config["type"] == "enum" and not isinstance(value, str):
            raise NADCommandError(f"Invalid value {value} for {setting}, not a string")

        if config["type"] == "string":
            command += str(value)
        elif config["type"] == "number":
            step = config.get("step", 1)
            if float(step).is_integer():
                command += str(round(float(value)))
            else:
                command += f"{round(float(value), 9):.9f}".rstrip("0").rstrip(".")
        elif config["type"] == "boolean" and isinstance(value, bool):
            command += config["values"][int(value)]
        elif config["type"] in ["boolean", "enum"]:
            matches = [v for v in config["values"] if v.lower() == str(value).lower()]
            if not matches:
                raise NADCommandError(f"Invalid value {value} for {setting}")
            command += matches[0]
        else:
            raise NADCommandError(f"Unsupported value type {config['type']}")

    return command
