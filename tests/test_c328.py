"""Tests for the NAD C328 amplifier.

The C328 steps its volume with `+` and `-` only, between -80 and 12 dB, and its sources
have fixed names.
"""

import pytest

from nad_serial import NADAmplifier, NADDevice
from nad_serial.exceptions import NADCommandError

from .simulation import SimulatedDevice

BUILD = "C328"
VALUES = {"Main.Volume": "-40", "Main.Source": "TV"}


async def test_source_names(url: str, device_simulation: SimulatedDevice):
    """The sources have fixed names instead of numbers."""
    device = await NADDevice.async_connect(url)
    assert isinstance(device, NADAmplifier)

    config = device.get_setting_config("Main.Source")
    assert config is not None
    assert config["values"] == [
        "TV",
        "PHONO",
        "COAX1",
        "COAX2",
        "OPT1",
        "OPT2",
        "STREAM",
        "BT",
    ]

    assert await device.async_set_source("PHONO")
    assert device_simulation.get("Main.Source") == "PHONO"
    with pytest.raises(NADCommandError):
        await device.async_set_source(1)
    with pytest.raises(NADCommandError):
        await device.async_set_source("CD")

    await device.async_disconnect()


async def test_volume_stepped(url: str, device_simulation: SimulatedDevice):
    """The volume can't be set directly, so it is stepped to the new value."""
    device = await NADDevice.async_connect(url)
    assert isinstance(device, NADAmplifier)

    assert await device.async_set_volume(-38)
    assert device_simulation.commands[-2:] == ["Main.Volume+", "Main.Volume+"]
    assert not any(
        command.startswith("Main.Volume=") for command in device_simulation.commands
    )
    assert device.volume == -38
    with pytest.raises(NADCommandError):
        await device.async_set_volume(13)

    await device.async_disconnect()
