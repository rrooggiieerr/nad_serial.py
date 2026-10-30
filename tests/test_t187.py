"""Tests for the NAD T187 surround preamplifier.

Firmware v2.20 of the T187 added and removed settings. From v2.20 it reports its volume
limits, for the main zone and Zone2 to Zone4.
"""

from typing import Any

import pytest

from nad_serial import NADAmplifier, NADDevice, NADMultiZoneReceiver
from nad_serial.exceptions import NADCommandError

from .simulation import SimulatedDevice

BUILD = "T187_PG536M_DAB"
VALUES = {"Main.Volume": "-40"}


async def test_zones(url: str, device_simulation: SimulatedDevice):
    """The device has 3 extra zones: Zone2, Zone3, Zone4."""
    device = await NADDevice.async_connect(url)
    assert isinstance(device, NADMultiZoneReceiver)
    assert device.zones is not None
    assert [zone.zone_number for zone in device.zones] == [2, 3, 4]

    await device.async_disconnect()


@pytest.mark.parametrize(
    ("device_simulation", "old_supported"),
    [({"firmware": "v2.10"}, True), ({"firmware": "v2.20"}, False)],
    indirect=["device_simulation"],
)
async def test_firmware_v2_20(
    url: str, device_simulation: SimulatedDevice, old_supported: bool
):
    """Firmware v2.20 removed Main.Speaker.Back.Config1 and added Main.Audio.CODEC."""
    device = await NADDevice.async_connect(url)

    assert device.firmware_version == device_simulation.firmware
    assert device.supports_setting("Main.Speaker.Back.Config1") is old_supported
    assert device.supports_setting("Main.Audio.CODEC") is not old_supported

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
        "Zone3.Volume.Min": "-80",
        "Zone3.Volume.Max": "6",
        "Zone4.Volume.Min": "-80",
        "Zone4.Volume.Max": "6",
    },
)
async def test_volume_limits(url: str, device_simulation: SimulatedDevice):
    """From firmware v2.20, the volume limits come from the device."""
    device = await NADDevice.async_connect(url)
    assert isinstance(device, NADAmplifier)

    assert _limits(device, "Main.Volume") == (-70, 10)
    assert _limits(device, "Zone2.Volume") == (-80, 6)
    assert _limits(device, "Zone3.Volume") == (-80, 6)
    assert _limits(device, "Zone4.Volume") == (-80, 6)
    with pytest.raises(NADCommandError):
        await device.async_set_volume(11)
    assert await device.async_set_volume(10)

    await device.async_disconnect()


@pytest.mark.simulated_device(firmware="v2.10")
async def test_volume_limits_older_firmware(
    url: str, device_simulation: SimulatedDevice
):
    """Before firmware v2.20, the documented limits -99 to 19 dB are used."""
    device = await NADDevice.async_connect(url)

    assert not device.supports_setting("Main.Volume.Min")
    assert not device.supports_setting("Main.Volume.Max")
    assert _limits(device, "Main.Volume") == (-99, 19)
    assert _limits(device, "Zone2.Volume") == (-99, 19)
    assert _limits(device, "Zone3.Volume") == (-99, 19)
    assert _limits(device, "Zone4.Volume") == (-99, 19)
    assert "Main.Volume.Max?" not in device_simulation.commands

    await device.async_disconnect()
