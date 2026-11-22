"""Tests for the NAD C388 amplifier.

The C388 reports its number of sources in Main.Sources, with 10 as the fallback, and sets
its volume directly between -70 and 10 dB.
"""

import pytest

from nad_serial import NADAmplifier, NADDevice, configs
from nad_serial.exceptions import NADCommandError

from .simulation import SimulatedDevice

BUILD = "C388"
VALUES = {"Main.Volume": "-40", "Main.Sources": "6", "Main.Source": "1"}


async def test_sources_config():
    """Main.Source refers to Main.Sources for its maximum, with 10 as the fallback."""
    settings = (await configs.async_read_device_config(BUILD))["settings"]
    assert settings["Main.Source"]["max"] == ["Main.Sources", 10]
    assert settings["Main.Sources"]["operators"] == "?"


async def test_volume_set(url: str, device_simulation: SimulatedDevice):
    """The volume is set directly with `=`, within -70 to 10 dB."""
    device = await NADDevice.async_connect(url)
    assert isinstance(device, NADAmplifier)

    assert await device.async_set_volume(-20)
    assert "Main.Volume=-20" in device_simulation.commands
    assert device.volume == -20
    with pytest.raises(NADCommandError):
        await device.async_set_volume(11)
    with pytest.raises(NADCommandError):
        await device.async_set_volume(-71)

    await device.async_disconnect()
