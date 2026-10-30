"""Tests for the NAD C356 amplifier.

The C356 has a motorised volume knob: the volume can only be stepped with `+` and `-`, and
isn't reported. It doesn't report its firmware version, and its sources have fixed names.
"""

import asyncio

import pytest

from nad_serial import NADAmplifier, NADDevice, configs
from nad_serial.exceptions import NADCommandError

from .simulation import SimulatedDevice

BUILD = "C356"
VALUES = {"Main.Source": "CD"}


async def test_async_read_device_config_c356():
    device_config = await configs.async_read_device_config("C356")
    assert device_config["settings"]["Main.Source"]["type"] == "enum"


async def test_source_names(url: str, device_simulation: SimulatedDevice):
    """The sources have fixed names instead of numbers."""
    device = await NADDevice.async_connect(url)
    assert isinstance(device, NADAmplifier)

    config = device.get_setting_config("Main.Source")
    assert config is not None
    assert config["values"] == ["Ipod", "CD", "Tuner", "Disc", "Aux", "Tape2", "Video"]

    assert await device.async_set_source("Tuner")
    assert device_simulation.get("Main.Source") == "Tuner"
    with pytest.raises(NADCommandError):
        await device.async_set_source(1)
    with pytest.raises(NADCommandError):
        await device.async_set_source("Phono")

    await device.async_disconnect()


async def test_volume_steps_only(url: str, device_simulation: SimulatedDevice):
    """The volume can be stepped, but not set to a value."""
    device = await NADDevice.async_connect(url)
    assert isinstance(device, NADAmplifier)

    assert "Main.Volume?" not in device_simulation.commands
    with pytest.raises(NADCommandError):
        await device.async_set_volume(-30)
    assert await device.async_increment("Main.Volume")
    assert await device.async_decrement("Main.Volume")
    await asyncio.sleep(
        0.05
    )  # Nothing is answered, so let the device handle the commands
    assert device_simulation.commands[-2:] == ["Main.Volume+", "Main.Volume-"]

    await device.async_disconnect()


async def test_no_firmware_version(url: str, device_simulation: SimulatedDevice):
    """The C356 doesn't report its firmware version."""
    device = await NADDevice.async_connect(url)

    assert not device.supports_setting("Main.Version")
    assert device.firmware_version is None

    await device.async_disconnect()
