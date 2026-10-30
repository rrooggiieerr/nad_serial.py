"""Tests the configuration file functions."""

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

    for setting in settings.values():
        assert setting["type"] in ("enum", "boolean", "string") or setting[
            "type"
        ].startswith("number")
        assert setting["operators"]
        assert setting["operators"] in ("=?", "=+-?", "?", "=", "+-", "+-?")
        if (
            setting["type"] == "number"
            and "?" in setting["operators"]
            and "+-" in setting["operators"]
        ):
            assert "min" in setting
            assert "max" in setting
        if setting["type"] in ("enum", "boolean"):
            assert setting["values"]
            # Validate that all values are case-insensitive unique
            lowered = [v.lower() for v in setting["values"]]
            assert len(lowered) == len(set(lowered))
        for key in ("min", "max", "step"):
            if (reference := setting.get(key)) is None:
                continue
            items = reference if isinstance(reference, list) else [reference]
            assert items, f"{key} is an empty list"
            for index, item in enumerate(items):
                if isinstance(item, str):
                    reference = item.split("[")[0]
                    type_ = settings.get(reference, {}).get("type")
                    assert type_ is not None
                    assert type_.startswith("number"), (
                        f"{key} refers to {item!r}, which is not a number setting"
                    )
                else:
                    assert not isinstance(item, bool), (
                        f"{key} item {item!r} is a boolean, not a number"
                    )
                    assert isinstance(item, (int, float)), (
                        f"{key} item {item!r} is not a number or a setting name"
                    )
                    assert index == len(items) - 1, (
                        f"{key} item {item!r}: only the last item may be a number"
                    )

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
