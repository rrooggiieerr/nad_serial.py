"""Tests the configuration file functions."""

import importlib.resources
from typing import Any

from packaging.specifiers import SpecifierSet
from packaging.version import Version
import pytest

from nad_serial import configs

BASE_CONFIGS = ("device", "amplifier", "tuner", "zones")

BUILDS = [
    "C328",
    "C338",
    "C356",
    "C368",
    "C388",
    "C427",
    "C399",
    "M15HD_PG536",
    "M15HD_PG536M",
    "M15HD_VXP",
    "M17_PG536M",
    "M51",
    "T175_PG10_DAB",
    "T175_PG10_XM",
    "T175_PG536_DAB",
    "T175_PG536_XM",
    "T175_PG536M_DAB",
    "T175_PG536M_XM",
    "T175_VXP_DAB",
    "T175_VXP_XM",
    "T187_PG536M_DAB",
    "T187_PG536M_XM",
    "T755_TXX3_DAB",
    "T755_TXX3_XM",
    "T757_PG536_DAB",
    "T757_PG536_XM",
    "T757_PG536M_DAB",
    "T757_PG536M_XM",
    "T758_PG536M_DAB",
    "T758_PG536M_NONE",
    "T765_PG10_DAB",
    "T765_PG10_XM",
    "T765_PG536_DAB",
    "T765_PG536_XM",
    "T765_PG536M_DAB",
    "T765_PG536M_XM",
    "T765_TXX3_DAB",
    "T765_TXX3_XM",
    "T765_VXP_DAB",
    "T765_VXP_XM",
    "T775_PG10_DAB",
    "T775_PG10_XM",
    "T775_PG536_DAB",
    "T775_PG536_XM",
    "T775_PG536M_DAB",
    "T775_PG536M_XM",
    "T775_VXP_DAB",
    "T775_VXP_XM",
    "T777_PG536M_DAB",
    "T777_PG536M_XM",
    "T778_PG536M_NONE",
    "T785_PG10_DAB",
    "T785_PG10_XM",
    "T785_PG536_DAB",
    "T785_PG536_XM",
    "T785_PG536M_DAB",
    "T785_PG536M_XM",
    "T785_VXP_DAB",
    "T785_VXP_XM",
    "T787_PG536M_DAB",
    "T787_PG536M_XM",
]


async def test_async_read_device_config_amplifier():
    """Test that an amplifier device only loads the `device.json` and `amplifier.json` config."""
    device_config = await configs.async_read_device_config("C356")
    assert device_config["device_types"] == ["amplifier"]
    assert device_config["settings"]["Main.Power"]
    assert device_config["settings"]["Main.Volume"]
    assert "Tuner.Band" not in device_config["settings"]
    assert device_config["settings"]["Main.Source"]


async def test_async_read_device_config_amplifier_zones():
    """Test that an amplifier device only loads the `device.json` and `amplifier.json` config."""
    device_config = await configs.async_read_device_config("T778")
    assert device_config["device_types"] == ["amplifier", "zones"]
    assert device_config["settings"]["Main.Power"]
    assert device_config["settings"]["Main.Volume"]
    assert "Tuner.Band" not in device_config["settings"]
    assert device_config["settings"]["Main.Source"]


async def test_async_read_device_config_tuner():
    """Test that a tuner device only loads the `device.json` and `tuner.json` config."""
    device_config = await configs.async_read_device_config("C427")
    assert device_config["device_types"] == ["tuner"]
    assert device_config["settings"]["Main.Power"]
    assert "Main.Volume" not in device_config["settings"]
    assert device_config["settings"]["Tuner.Band"]
    assert device_config["settings"]["Tuner.FM.Mute"]


async def test_async_read_device_config_receiver():
    """Test that a receiver device loads both the `device.json`, `amplifier.json` and `tuner.json` config."""
    device_config = await configs.async_read_device_config("T755")
    assert device_config["device_types"] == ["amplifier", "tuner", "zones"]
    assert device_config["settings"]["Main.Power"]
    assert device_config["settings"]["Main.Volume"]
    assert device_config["settings"]["Tuner.Band"]
    assert device_config["settings"]["DSP.Version"]


async def test_async_read_build_config_receiver_dab():
    """Test that a receiver device with DAB loads the `device.json`, `tuner.json` and `dab.json` config."""
    device_config = await configs.async_read_device_config("T755_TXX3_DAB")
    assert device_config["device_types"] == ["amplifier", "tuner", "zones"]
    assert device_config["settings"]["Main.Power"]
    assert device_config["settings"]["Main.Volume"]
    assert device_config["settings"]["Tuner.Band"]
    assert device_config["settings"]["Tuner.Band"]["values"] == ["FM", "AM", "DAB"]
    assert device_config["settings"]["Tuner.FM.Mute"]
    assert device_config["settings"]["Tuner.DAB.DLS"]
    assert device_config["settings"]["Tuner.DAB.Service"]


async def test_async_read_build_config_receiver_xm():
    """Test that a receiver device with XM loads the `device.json`, `tuner.json` and `xm.json` config."""
    device_config = await configs.async_read_device_config("T755_TXX3_XM")
    assert device_config["device_types"] == ["amplifier", "tuner", "zones"]
    assert device_config["settings"]["Main.Power"]
    assert device_config["settings"]["Tuner.Band"]
    assert device_config["settings"]["Tuner.Band"]["values"] == ["FM", "AM", "XM"]
    assert device_config["settings"]["Tuner.FM.Mute"]
    assert device_config["settings"]["Tuner.XM.Channel"]
    assert device_config["settings"]["Tuner.XM.ChannelName"]
    assert device_config["settings"]["Tuner.XM.Name"]
    assert device_config["settings"]["Tuner.XM.Title"]


async def test_async_read_device_config_none_device():
    """Test that an unknown device only loads the `device.json` config."""
    device_config = await configs.async_read_device_config(None)
    assert "device_types" not in device_config
    assert device_config["settings"]["Main.Power"]
    assert "Main.Volume" not in device_config["settings"]
    assert "Tuner.Band" not in device_config["settings"]
    assert "DSP.Version" not in device_config["settings"]


async def test_async_read_device_config_unknown_device():
    """Test that an unknown device only loads the `device.json` config."""
    device_config = await configs.async_read_device_config("X000")
    assert "device_types" not in device_config
    assert device_config["settings"]["Main.Power"]
    assert "Main.Volume" not in device_config["settings"]
    assert "Tuner.Band" not in device_config["settings"]
    assert "DSP.Version" not in device_config["settings"]


async def test_async_read_device_config_unknown_device_detected_amplifier():
    """Test that an unknown device only loads the `device.json` and `amplifier.json` config."""
    device_config = await configs.async_read_device_config("X000", ["amplifier"])
    assert device_config["device_types"] == ["amplifier"]
    assert device_config["settings"]["Main.Power"]
    assert device_config["settings"]["Main.Volume"]
    assert "Tuner.Band" not in device_config["settings"]
    assert "DSP.Version" not in device_config["settings"]


async def test_async_read_device_config_unknown_device_detected_tuner():
    """Test that an unknown device only loads the `device.json` and `tuner.json` config."""
    device_config = await configs.async_read_device_config("X000", ["tuner"])
    assert device_config["device_types"] == ["tuner"]
    assert device_config["settings"]["Main.Power"]
    assert "Main.Volume" not in device_config["settings"]
    assert device_config["settings"]["Tuner.Band"]
    assert "DSP.Version" not in device_config["settings"]


async def test_async_read_device_config_unknown_device_detected_receiver():
    """Test that an unknown device only loads the `device.json`, `amplifier.json` and `tuner.json` config."""
    device_config = await configs.async_read_device_config(
        "X000", ["amplifier", "tuner"]
    )
    assert device_config["device_types"] == ["amplifier", "tuner"]
    assert device_config["settings"]["Main.Power"]
    assert device_config["settings"]["Main.Volume"]
    assert device_config["settings"]["Tuner.Band"]
    assert "DSP.Version" not in device_config["settings"]


async def test_async_read_device_config_unknown_build_detected_receiver_dab():
    """Test that an unknown device only loads the `device.json`, `amplifier.json` and `tuner.json` config."""
    device_config = await configs.async_read_device_config(
        "X000_TXX3_DAB", ["amplifier", "tuner"]
    )
    assert device_config["device_types"] == ["amplifier", "tuner"]
    assert device_config["settings"]["Main.Power"]
    assert device_config["settings"]["Main.Volume"]
    assert device_config["settings"]["Tuner.Band"]
    assert device_config["settings"]["Tuner.Band"]["values"] == ["FM", "AM", "DAB"]
    assert device_config["settings"]["Tuner.FM.Mute"]
    assert device_config["settings"]["Tuner.DAB.DLS"]
    assert device_config["settings"]["Tuner.DAB.Service"]
    assert "DSP.Version" not in device_config["settings"]


async def test_async_read_device_config_unknown_build_detected_receiver_xm():
    """Test that an unknown device only loads the `device.json`, `amplifier.json` and `tuner.json` config."""
    device_config = await configs.async_read_device_config(
        "X000_TXX3_XM", ["amplifier", "tuner"]
    )
    assert device_config["device_types"] == ["amplifier", "tuner"]
    assert device_config["settings"]["Main.Power"]
    assert device_config["settings"]["Main.Volume"]
    assert device_config["settings"]["Tuner.Band"]
    assert device_config["settings"]["Tuner.Band"]["values"] == ["FM", "AM", "XM"]
    assert device_config["settings"]["Tuner.FM.Mute"]
    assert device_config["settings"]["Tuner.XM.Channel"]
    assert device_config["settings"]["Tuner.XM.ChannelName"]
    assert device_config["settings"]["Tuner.XM.Name"]
    assert device_config["settings"]["Tuner.XM.Title"]
    assert "DSP.Version" not in device_config["settings"]


_CONFIG_KEYS = {"device_types", "sends_updates", "settings"}
_SETTING_KEYS = {
    "description",
    "firmware",
    "latest",
    "max",
    "min",
    "operators",
    "regex",
    "step",
    "type",
    "unit",
    "values",
}
_TYPES = ("boolean", "boolean[]", "enum", "number", "number[]", "string")
_OPERATORS = ("=?", "=+-?", "?", "=", "+-", "+-?")
# Modules have no configuration file of their own, or extend a model
_MODULES = {"dab", "none", "pg10", "pg536", "pg536m", "txx3", "vxp", "xm"}


def _validate_setting(
    name: str, setting: dict[str, Any], settings: dict[str, dict[str, Any]]
) -> None:
    """Validates a setting against the specification in the configs README."""
    assert set(setting) <= _SETTING_KEYS, f"{name}: unknown keys"
    assert setting["type"] in _TYPES, f"{name}: unknown type {setting['type']}"
    assert setting["operators"] in _OPERATORS, f"{name}: invalid operators"

    if setting["type"].endswith("[]"):
        assert "+" not in setting["operators"], f"{name}: a list can't be stepped"

    if setting["type"] in ("boolean", "boolean[]", "enum"):
        values = setting.get("values")
        assert values, f"{name}: no values"
        assert all(isinstance(value, str) for value in values), (
            f"{name}: values must be strings"
        )
        lowered = [value.lower() for value in values]
        assert len(lowered) == len(set(lowered)), f"{name}: values not unique"
    if setting["type"] in ("boolean", "boolean[]"):
        assert len(setting["values"]) == 2, (
            f"{name}: a boolean has an off and an on value"
        )

    if any(key in setting for key in ("min", "max", "step")):
        assert setting["type"] == "number", f"{name}: min, max and step are for numbers"
    if (
        setting["type"] == "number"
        and "?" in setting["operators"]
        and "+" in setting["operators"]
    ):
        assert "min" in setting, f"{name}: no min"
        assert "max" in setting, f"{name}: no max"

    for key in ("min", "max", "step"):
        if (reference := setting.get(key)) is None:
            continue
        items = reference if isinstance(reference, list) else [reference]
        assert items, f"{name}: {key} is an empty list"
        for position, item in enumerate(items):
            if isinstance(item, str):
                _validate_reference(name, key, item, settings)
            else:
                assert not isinstance(item, bool), (
                    f"{name}: {key} {item!r} is a boolean"
                )
                assert isinstance(item, (int, float)), (
                    f"{name}: {key} {item!r} is not a number or a setting name"
                )
                assert position == len(items) - 1, (
                    f"{name}: {key} {item!r}, only the last item may be a number"
                )


def _validate_reference(
    name: str, key: str, reference: str, settings: dict[str, dict[str, Any]]
) -> None:
    """Validates a reference to a setting, optionally indexed: Main.VolumeLimits[0]."""
    setting_name, _, index = reference.partition("[")
    if index:
        assert index.endswith("]"), f"{name}: {key} {reference!r} has no closing ]"
        assert index[:-1].isdecimal(), (
            f"{name}: {key} {reference!r} has an invalid index"
        )
    assert setting_name in settings, f"{name}: {key} refers to unknown {setting_name}"
    type_ = settings[setting_name]["type"]
    assert type_ == ("number[]" if index else "number"), (
        f"{name}: {key} {reference!r} refers to a {type_}"
    )


@pytest.mark.parametrize(
    "build",
    BUILDS,
)
async def test_all_builds(build: str):
    """Tests if all configuration files follow the specification."""
    device_config = await configs.async_read_device_config(build)
    assert "device_types" in device_config

    for device_type in device_config["device_types"]:
        assert device_type in BASE_CONFIGS

    assert "settings" in device_config
    settings = device_config["settings"]

    assert set(device_config) <= _CONFIG_KEYS
    assert isinstance(device_config.get("sends_updates", False), bool)

    for name, setting in settings.items():
        _validate_setting(name, setting, settings)

    # The latest known version of each version setting, e.g. Main.Version or DSP.Version
    for name, setting in settings.items():
        if (latest := setting.get("latest")) is None:
            continue
        assert "Version" in name.split("."), (
            f"{name}: latest is only for version settings"
        )
        assert isinstance(latest, str), f"{name}: latest {latest!r} is not a string"
        Version(latest)  # Raises InvalidVersion when invalid

    # Firmware conditions refer to the main firmware version
    latest = settings.get("Main.Version", {}).get("latest")
    latest_version = Version(latest) if latest is not None else None

    # The firmware versions that support a setting
    for name, setting in settings.items():
        if (condition := setting.get("firmware")) is None:
            continue
        assert isinstance(condition, str), (
            f"{name}: firmware {condition!r} is not a string"
        )
        specifiers = SpecifierSet(condition)  # Raises InvalidSpecifier when invalid
        assert len(specifiers) > 0, f"{name}: firmware is empty"
        if latest_version is not None:
            for specifier in specifiers:
                assert Version(specifier.version) <= latest_version, (
                    f"{name}: firmware {condition!r} refers to a version after latest {latest!r}"
                )


def test_all_models_tested():
    """Every model configuration file is used by at least one build in BUILDS."""
    models = (
        {
            resource.name.removesuffix(".json")
            for resource in importlib.resources.files("nad_serial.configs").iterdir()
            if resource.name.endswith(".json")
        }
        - set(BASE_CONFIGS)
        - _MODULES
    )
    tested = {build.split("_")[0].lower() for build in BUILDS}
    assert models <= tested, f"Add a build for {sorted(models - tested)} to BUILDS"


def test_deep_merge():
    """Test deep merging two dictionaties."""
    dict1 = {
        "settings": {
            "Main.Power": {
                "operators": "=+-?",
                "type": "boolean",
                "values": ["Off", "On"],
            }
        }
    }
    dict2 = {
        "settings": {
            "Main.Volume": {
                "description": "Set the volume in dB",
                "max": 19,
                "min": -99,
                "operators": "+-?",
                "type": "number",
                "unit": "dB",
            }
        }
    }
    configs._deep_merge(dict1, dict2)
    assert dict1["settings"]["Main.Power"]["operators"] == "=+-?"
    assert dict1["settings"]["Main.Volume"]


def test_deep_merge_updated_value():
    """Test deep merging two dictionaties with an updated value."""
    dict1 = {
        "settings": {
            "Main.Power": {"operators": "?", "type": "boolean", "values": ["Off", "On"]}
        }
    }
    dict2 = {
        "settings": {
            "Main.Volume": {
                "description": "Set the volume in dB",
                "max": 19,
                "min": -99,
                "operators": "+-?",
                "type": "number",
                "unit": "dB",
            }
        }
    }
    configs._deep_merge(dict1, dict2)
    assert dict1["settings"]["Main.Power"]["operators"] == "?"
    assert dict1["settings"]["Main.Volume"]


def test_deep_merge_deleted_value():
    """Test deep merging two dictionaties with a deleted value."""
    dict1 = {
        "settings": {
            "Main.Power": {
                "operators": "=+-?",
                "type": "boolean",
                "values": ["Off", "On"],
            }
        }
    }
    dict2 = {
        "settings": {
            "Main.Power": None,
            "Main.Volume": {
                "description": "Set the volume in dB",
                "max": 19,
                "min": -99,
                "operators": "+-?",
                "type": "number",
                "unit": "dB",
            },
        }
    }
    configs._deep_merge(dict1, dict2)
    assert "Main.Power" not in dict1["settings"]
    assert dict1["settings"]["Main.Volume"]
