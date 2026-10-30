"""Tests for the NAD T775 receiver.

The T775 has a tuner and zones, and sets its volume directly between -99 and 19 dB.
"""

import pytest

from nad_serial import NADAmplifier, NADDevice, NADMultiZoneReceiver
from nad_serial.exceptions import NADCommandError

from .simulation import SimulatedDevice

BUILD = "T775_PG536M_DAB"
VALUES = {"Main.Volume": "-40"}


async def test_device_class(url: str, device_simulation: SimulatedDevice):
    """The T775 has an amplifier, a tuner and zones."""
    device = await NADDevice.async_connect(url)
    assert type(device) is NADMultiZoneReceiver

    await device.async_disconnect()


async def test_volume_set(url: str, device_simulation: SimulatedDevice):
    """The volume is set directly with `=`, within -99 to 19 dB."""
    device = await NADDevice.async_connect(url)
    assert isinstance(device, NADAmplifier)

    assert await device.async_set_volume(-20)
    assert "Main.Volume=-20" in device_simulation.commands
    assert device.volume == -20
    with pytest.raises(NADCommandError):
        await device.async_set_volume(20)
    with pytest.raises(NADCommandError):
        await device.async_set_volume(-100)

    await device.async_disconnect()
