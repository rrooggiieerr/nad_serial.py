"""Tests the configuration file functions."""

import pytest

from nad_serial import configs


async def test_async_read_device_config_amplifier():
    """Test that an amplifier device type only loads the `device,json` and `amplifier.json` config."""
    device_config = await configs.async_read_device_config("C356")
    assert device_config["device_types"] == ["amplifier"]
    assert device_config["settings"]["Main.Power"]
    assert device_config["settings"]["Main.Volume"]
    assert "Tuner.Band" not in device_config["settings"]
    assert device_config["settings"]["Main.Source"]


async def test_async_read_device_config_tuner():
    """Test that an amplifier device type only loads the `device,json` and `tuner.json` config."""
    device_config = await configs.async_read_device_config("C427")
    assert device_config["device_types"] == ["tuner"]
    assert device_config["settings"]["Main.Power"]
    assert "Main.Volume" not in device_config["settings"]
    assert device_config["settings"]["Tuner.Band"]
    assert device_config["settings"]["Tuner.FM.Mute"]


async def test_async_read_device_config_receiver():
    """Test that an amplifier device type loads both the `device,json`, `amplifier.json` and `tuner.json` config."""
    device_config = await configs.async_read_device_config("T755")
    assert device_config["device_types"] == ["amplifier", "tuner", "zones"]
    assert device_config["settings"]["Main.Power"]
    assert device_config["settings"]["Main.Volume"]
    assert device_config["settings"]["Tuner.Band"]
    assert device_config["settings"]["DSP.Version"]


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


@pytest.mark.parametrize(
    "model",
    (
        "C356",
        "C368",
        "C388",
        "C427",
        "M15HD",
        "T175",
        "T187",
        "T755",
        "T757",
        "T765",
        "T775",
        "T777",
        "T785",
        "T787",
    ),
)
async def test_all_files(model: str):
    """Tests if all configuration files follow the specification."""
    device_config = await configs.async_read_device_config(model)
    assert "device_types" in device_config

    for device_type in device_config["device_types"]:
        assert device_type in ["amplifier", "tuner", "zones"]

    for setting in device_config["settings"].values():
        assert setting["type"] in ("number", "enum", "boolean", "string")
        assert setting["operators"]
        if "+" in setting["operators"]:
            # Make sure +- is always in that order
            assert "+-" in setting["operators"]
        if (
            setting["type"] == "number"
            and "?" in setting["operators"]
            and "+-" in setting["operators"]
        ):
            assert "min" in setting
            assert "max" in setting
        if setting["type"] in ("enum", "boolean"):
            assert setting["values"]


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
