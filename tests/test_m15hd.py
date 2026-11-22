"""Tests for the NAD M15HD surround preamplifier.

From firmware v1.32 the M15HD reports its volume limits, for the main zone and Zone2. It
has 9 sources and three extra zones.
"""

import pytest

from nad_serial import NADAmplifier, NADDevice, NADMultiZoneAmplifier, configs
from nad_serial.exceptions import NADCommandError

from .simulation import SimulatedDevice

BUILD = "M15HD_PG536M"
VALUES = {"Main.Volume": "-40", "Main.Source": "1"}


async def test_zones(url: str, device_simulation: SimulatedDevice):
    """The device has 3 extra zones: Zone2, Zone3, Zone4."""
    device = await NADDevice.async_connect(url)
    assert isinstance(device, NADMultiZoneAmplifier)
    assert device.zones is not None
    assert [zone.zone_number for zone in device.zones] == [2, 3, 4]

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
    assert settings["Main.Volume"]["min"] == ["Main.Volume.Min", -99]
    assert settings["Main.Volume"]["max"] == ["Main.Volume.Max", 19]
    assert settings["Zone2.Volume"]["min"] == ["Zone2.Volume.Min", -99]
    assert settings["Zone2.Volume"]["max"] == ["Zone2.Volume.Max", 19]


@pytest.mark.parametrize(("version", "supported"), [("v1.32", True), ("v1.30", False)])
async def test_volume_limits_firmware(version: str, supported: bool):
    """The device reports its volume limits from firmware v1.32."""
    config = await configs.async_read_device_config(BUILD, version=version)
    settings = config["settings"]
    for setting in (
        "Main.Volume.Min",
        "Main.Volume.Max",
        "Zone2.Volume.Min",
        "Zone2.Volume.Max",
    ):
        assert (setting in settings) is supported, setting
