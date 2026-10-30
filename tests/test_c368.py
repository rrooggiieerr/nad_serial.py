"""Tests for the NAD C368 amplifier.

The C368 reports its number of sources in Main.Sources, and sets its volume directly
between -70 and 10 dB.
"""

import asyncio

import pytest

from nad_serial import NADAmplifier, NADDevice, configs
from nad_serial.exceptions import NADCommandError

from .simulation import SimulatedDevice

BUILD = "C368"
VALUES = {"Main.Volume": "-40", "Main.Sources": "6", "Main.Source": "1"}


async def test_async_read_device_config_c368():
    device_config = await configs.async_read_device_config("C368")
    assert device_config["settings"]["Main.Sources"]["operators"] == "?"


@pytest.mark.simulated_device(values={"Main.Sources": "6", "Main.Source": "1"})
async def test_sources(url: str, device_simulation: SimulatedDevice):
    """The number of sources comes from Main.Sources."""
    device = await NADDevice.async_connect(url)
    assert isinstance(device, NADAmplifier)

    config = device.get_setting_config("Main.Source")
    assert config is not None
    assert config["max"] == 6
    with pytest.raises(NADCommandError):
        await device.async_set_source(7)
    assert await device.async_set_source(6)

    device_simulation.send("Main.Sources=8")
    await asyncio.sleep(0.05)  # Let the reader loop handle the line
    config = device.get_setting_config("Main.Source")
    assert config is not None
    assert config["max"] == 8

    await device.async_disconnect()


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
