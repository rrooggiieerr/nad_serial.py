"""Tests for the NAD M51 DAC.

The M51 reports its firmware version with a capital V, e.g. V1.50. Its sources have fixed
names, some with a space, and its volume is set directly between -90 and 10 dB.
"""

import pytest

from nad_serial import NADAmplifier, NADDevice
from nad_serial.exceptions import NADCommandError

from .simulation import SimulatedDevice

BUILD = "M51"
VALUES = {"Main.Volume": "-40", "Main.Source": "USB"}


async def test_source_names(url: str, device_simulation: SimulatedDevice):
    """The sources have fixed names instead of numbers."""
    device = await NADDevice.async_connect(url)
    assert isinstance(device, NADAmplifier)

    config = device.get_setting_config("Main.Source")
    assert config is not None
    assert config["values"] == [
        "AES",
        "COAX",
        "OPT",
        "USB",
        "HDMI 1",
        "HDMI 2",
        "PC LINK",
    ]

    assert await device.async_set_source("HDMI 1")
    assert device_simulation.get("Main.Source") == "HDMI 1"
    with pytest.raises(NADCommandError):
        await device.async_set_source(1)
    with pytest.raises(NADCommandError):
        await device.async_set_source("HDMI")

    await device.async_disconnect()


async def test_volume_set(url: str, device_simulation: SimulatedDevice):
    """The volume is set directly with `=`, within -90 to 10 dB."""
    device = await NADDevice.async_connect(url)
    assert isinstance(device, NADAmplifier)

    assert await device.async_set_volume(-20)
    assert "Main.Volume=-20" in device_simulation.commands
    assert device.volume == -20
    with pytest.raises(NADCommandError):
        await device.async_set_volume(11)
    with pytest.raises(NADCommandError):
        await device.async_set_volume(-91)

    await device.async_disconnect()


async def test_firmware_version(url: str, device_simulation: SimulatedDevice):
    """The firmware version is reported with a capital V."""
    device = await NADDevice.async_connect(url)

    assert device.firmware_version == "V1.50"

    await device.async_disconnect()
