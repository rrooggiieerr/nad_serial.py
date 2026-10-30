"""Tests for the NAD T757 receiver.

The T757 reports changes on its own. From firmware v2.20 it reports its volume limits;
before, the main zone goes down to -92 dB.
"""

from typing import Any

import pytest

from nad_serial import NADAmplifier, NADDevice
from nad_serial.exceptions import NADCommandError

from .simulation import SimulatedDevice

BUILD = "T757_PG536M_DAB"
VALUES = {"Main.Volume": "-40"}


async def test_sends_updates(url: str, device_simulation: SimulatedDevice):
    """The configuration says that the device reports changes on its own."""
    device = await NADDevice.async_connect(url)
    assert device.sends_updates is True

    await device.async_disconnect()


def _limits(device: NADDevice, setting: str) -> tuple[Any, Any]:
    config = device.get_setting_config(setting)
    assert config is not None
    return config.get("min"), config.get("max")


@pytest.mark.simulated_device(
    firmware="v2.20",
    values={
        "Main.Volume.Min": "-70",
        "Main.Volume.Max": "10",
        "Zone2.Volume.Min": "-80",
        "Zone2.Volume.Max": "6",
    },
)
async def test_volume_limits(url: str, device_simulation: SimulatedDevice):
    """From firmware v2.20, the volume limits come from the device."""
    device = await NADDevice.async_connect(url)
    assert isinstance(device, NADAmplifier)

    assert _limits(device, "Main.Volume") == (-70, 10)
    assert _limits(device, "Zone2.Volume") == (-80, 6)
    with pytest.raises(NADCommandError):
        await device.async_set_volume(11)
    assert await device.async_set_volume(10)

    await device.async_disconnect()


@pytest.mark.simulated_device(firmware="v2.10")
async def test_volume_limits_older_firmware(
    url: str, device_simulation: SimulatedDevice
):
    """Before firmware v2.20, the documented limits -92 to 19 dB are used."""
    device = await NADDevice.async_connect(url)

    assert not device.supports_setting("Main.Volume.Min")
    assert not device.supports_setting("Main.Volume.Max")
    assert _limits(device, "Main.Volume") == (-92, 19)
    assert _limits(device, "Zone2.Volume") == (-99, 19)
    assert "Main.Volume.Max?" not in device_simulation.commands

    await device.async_disconnect()
