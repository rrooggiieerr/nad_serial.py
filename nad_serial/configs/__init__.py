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
    config_file = "".join(c if c.isalnum() else "" for c in config) + ".json"

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
    build: str | None = None, detected_device_types: list[str] | None = None
) -> dict[str, Any]:
    """Reads the device configuration."""
    build_config = None
    device_types = ["device"]
    device_config: dict[str, Any] = {}

    if build:
        parts = build.casefold().split("_")
        while "none" in parts:
            parts.remove("none")
        parts.reverse()

        for part in parts:
            config = await _async_read_config_file(part)
            if config is None:
                continue

            if build_config is None:
                build_config = config
            else:
                _deep_merge(build_config, config)

    if detected_device_types:
        for item in detected_device_types:
            if item not in device_types:
                device_types.append(item)
    if build_config is not None:
        for item in build_config.get("device_types", []):
            if item not in device_types:
                device_types.append(item)

    for device_type in device_types:
        _deep_merge(device_config, await _async_read_config_file(device_type) or {})

    if build_config:
        _deep_merge(device_config, build_config)
    if len(device_types) > 1:
        device_config["device_types"] = device_types[1:]

    return device_config
