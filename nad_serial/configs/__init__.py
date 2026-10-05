"""Configuration files for NAD devices."""

import asyncio
import copy
import importlib.resources
import json
from json.decoder import JSONDecodeError
import logging
from typing import Any

logger = logging.getLogger(__name__)


def _deep_merge(dict1: dict[str, Any], dict2: dict[str, Any]) -> dict[str, Any]:
    """Merges dict2 into dict1. A null in dict2 removes the value in dict1."""
    for key, value in dict2.items():
        if value is None:
            dict1.pop(key, None)
        elif isinstance(value, dict):
            if not isinstance(dict1.get(key), dict):
                dict1[key] = {}
            _deep_merge(dict1[key], value)
        else:
            dict1[key] = copy.deepcopy(value)
    return dict1


async def _async_read_config_file(config: str) -> dict[str, Any] | None:
    config_file = (
        "".join(c if c.isalnum() or c in "._-" else "_" for c in config.lower())
        + ".json"
    )

    try:
        path = importlib.resources.files("nad_serial.configs").joinpath(config_file)
        data = await asyncio.to_thread(
            lambda: json.loads(path.read_text(encoding="utf-8"))
        )
    except FileNotFoundError:
        logger.debug("Configuration file %s not found", config_file)
        return None
    except IsADirectoryError, PermissionError:
        logger.exception("Configuration file %s not accessible", config_file)
        return None
    except UnicodeDecodeError:
        logger.exception("Invalid configuration file %s, Unicode error", config_file)
        return None
    except JSONDecodeError:
        logger.exception("Invalid configuration file %s, JSON error", config_file)
        return None

    if not isinstance(data, dict):
        logger.error("Invalid configuration file %s", config_file)
        return None

    return data


async def async_read_device_config(
    model: str | None = None, detected_device_types: list[str] | None = None
) -> dict[str, Any]:
    """Reads the device configuration."""
    device_types = ["device"]
    device_config: dict[str, Any] = {}

    model_config = None
    if model:
        model_config = await _async_read_config_file(model)

    if model_config is not None:
        device_types += model_config.get("device_types", [])
    elif detected_device_types:
        device_types += detected_device_types

    for device_type in device_types:
        _deep_merge(device_config, await _async_read_config_file(device_type) or {})

    if model_config is not None:
        _deep_merge(device_config, model_config)
    elif detected_device_types:
        device_config["device_types"] = list(detected_device_types)

    return device_config
