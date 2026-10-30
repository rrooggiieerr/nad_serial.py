"""Tests for the NAD C338 amplifier.

The C338 sets its volume in steps of 0.5 dB, and its sources have fixed names.
"""

import asyncio

import pytest

from nad_serial import NADAmplifier, NADDevice
from nad_serial.exceptions import NADCommandError

from .simulation import SimulatedDevice

BUILD = "C338"
VALUES = {"Main.Volume": "-40", "Main.Source": "Stream"}


async def test_source_names(url: str, device_simulation: SimulatedDevice):
    """The sources have fixed names instead of numbers."""
    device = await NADDevice.async_connect(url)
    assert isinstance(device, NADAmplifier)

    config = device.get_setting_config("Main.Source")
    assert config is not None
    assert config["values"] == [
        "Stream",
        "Wireless",
        "TV",
        "Phono",
        "Coax1",
        "Coax2",
        "Opt1",
        "Opt2",
    ]

    assert await device.async_set_source("Phono")
    assert device_simulation.get("Main.Source") == "Phono"
    with pytest.raises(NADCommandError):
        await device.async_set_source(1)
    with pytest.raises(NADCommandError):
        await device.async_set_source("CD")

    await device.async_disconnect()


async def test_volume_half_steps(url: str, device_simulation: SimulatedDevice):
    """The volume is set and read in steps of 0.5 dB."""
    device = await NADDevice.async_connect(url)
    assert isinstance(device, NADAmplifier)

    assert await device.async_set_volume(-30.5)
    assert "Main.Volume=-30.5" in device_simulation.commands
    assert device.volume == -30.5
    assert await device.async_request_volume() == -30.5

    # A whole number is still a valid volume
    assert await device.async_set_volume(-30)
    assert device.volume == -30

    device_simulation.send("Main.Volume=-29.5")
    await asyncio.sleep(0.05)  # Let the reader loop handle the line
    assert device.volume == -29.5

    await device.async_disconnect()
