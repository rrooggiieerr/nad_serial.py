"""Tests for the NAD T778 receiver.

The T778 has no tuner, reports changes on its own and has 9 sources. From firmware v2.20 it
reports its volume limits; before, the main zone goes down to -92 dB.
"""

import pytest

from nad_serial import NADAmplifier, NADDevice, NADMultiZoneAmplifier, configs
from nad_serial.exceptions import NADCommandError

from .simulation import SimulatedDevice

BUILD = "T778_PG536M_NONE"
VALUES = {"Main.Volume": "-40", "Main.Source": "1"}


async def test_device_class(url: str, device_simulation: SimulatedDevice):
    """The T778 has an amplifier and zones, but no tuner."""
    device = await NADDevice.async_connect(url)
    assert type(device) is NADMultiZoneAmplifier

    await device.async_disconnect()


async def test_sends_updates(url: str, device_simulation: SimulatedDevice):
    """The configuration says that the device reports changes on its own."""
    device = await NADDevice.async_connect(url)
    assert device.sends_updates is True

    await device.async_disconnect()


async def test_source_max(url: str, device_simulation: SimulatedDevice):
    """There are 9 sources."""
    device = await NADDevice.async_connect(url)
    assert isinstance(device, NADAmplifier)

    with pytest.raises(NADCommandError):
        await device.async_set_source(10)
    assert await device.async_set_source(9)

    await device.async_disconnect()


async def test_volume_limits_config():
    """The volume limits come from the device, with the documented limits as the fallback."""
    settings = (await configs.async_read_device_config(BUILD))["settings"]
    assert settings["Main.Volume"]["min"] == ["Main.Volume.Min", -92]
    assert settings["Main.Volume"]["max"] == ["Main.Volume.Max", 19]
    assert settings["Zone2.Volume"]["min"] == ["Zone2.Volume.Min", -99]
    assert settings["Zone2.Volume"]["max"] == ["Zone2.Volume.Max", 19]


@pytest.mark.parametrize(("version", "supported"), [("v2.20", True), ("v2.10", False)])
async def test_volume_limits_firmware(version: str, supported: bool):
    """The device reports its volume limits from firmware v2.20."""
    config = await configs.async_read_device_config(BUILD, version=version)
    settings = config["settings"]
    for setting in (
        "Main.Volume.Min",
        "Main.Volume.Max",
        "Zone2.Volume.Min",
        "Zone2.Volume.Max",
    ):
        assert (setting in settings) is supported, setting
