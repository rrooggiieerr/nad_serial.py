"""Tests for the NAD T755 receiver.

The T755 reports changes on its own, and sets its volume directly between -96 and 15 dB.
"""

import pytest

from nad_serial import NADAmplifier, NADDevice
from nad_serial.exceptions import NADCommandError

from .simulation import SimulatedDevice

BUILD = "T755_TXX3_DAB"
VALUES = {"Main.Volume": "-40"}


async def test_sends_updates(url: str, device_simulation: SimulatedDevice):
    """The configuration says that the device reports changes on its own."""
    device = await NADDevice.async_connect(url)
    assert device.sends_updates is True

    await device.async_disconnect()


async def test_volume_set(url: str, device_simulation: SimulatedDevice):
    """The volume is set directly with `=`, within -96 to 15 dB."""
    device = await NADDevice.async_connect(url)
    assert isinstance(device, NADAmplifier)

    assert await device.async_set_volume(-20)
    assert "Main.Volume=-20" in device_simulation.commands
    assert device.volume == -20
    with pytest.raises(NADCommandError):
        await device.async_set_volume(16)
    with pytest.raises(NADCommandError):
        await device.async_set_volume(-97)

    await device.async_disconnect()
