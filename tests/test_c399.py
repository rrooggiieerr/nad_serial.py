"""Tests the volume limits of the NAD C399, which reports them in Main.VolumeLimits.

The C399 reports its volume limits as one setting with a list of numbers, e.g.
`Main.VolumeLimits=-60,12`. Main.Volume refers to them as `Main.VolumeLimits[0]` and
`Main.VolumeLimits[1]`, with -80 and 12 as the fallback. The number of sources comes from
Main.Sources, with 10 as the fallback. Setting a list isn't supported.
"""

import asyncio
from typing import Any

import pytest

from nad_serial import NADAmplifier, NADDevice
from nad_serial.configs import async_read_device_config
from nad_serial.exceptions import NADCommandError

from .simulation import SimulatedDevice

BUILD = "C399"
VALUES = {"Main.Volume": "-30", "Main.VolumeLimits": "-60,12"}


def _volume_limits(device: NADDevice) -> tuple[Any, Any]:
    config = device.get_setting_config("Main.Volume")
    assert config is not None
    return config.get("min"), config.get("max")


async def test_config():
    """Main.VolumeLimits is a list of numbers, and Main.Volume refers to its items."""
    settings = (await async_read_device_config(BUILD))["settings"]
    assert settings["Main.VolumeLimits"]["type"] == "number[]"
    assert settings["Main.Volume"]["min"] == ["Main.VolumeLimits[0]", -80]
    assert settings["Main.Volume"]["max"] == ["Main.VolumeLimits[1]", 12]


async def test_volume_limits(url: str, device_simulation: SimulatedDevice):
    """The volume limits come from Main.VolumeLimits."""
    device = await NADDevice.async_connect(url)
    assert isinstance(device, NADAmplifier)
    assert _volume_limits(device) == (-60, 12)

    with pytest.raises(NADCommandError):
        await device.async_set_volume(13)
    with pytest.raises(NADCommandError):
        await device.async_set_volume(-61)
    assert await device.async_set_volume(-28)
    assert device.volume == -28

    await device.async_disconnect()


async def test_volume_limits_changed(url: str, device_simulation: SimulatedDevice):
    """New volume limits reported by the device are used right away."""
    device = await NADDevice.async_connect(url)

    device_simulation.send("Main.VolumeLimits=-50,6")
    await asyncio.sleep(0.05)  # Let the reader loop handle the line

    assert _volume_limits(device) == (-50, 6)
    with pytest.raises(NADCommandError):
        await device.async_set_volume(7)

    await device.async_disconnect()


@pytest.mark.parametrize(
    ("device_simulation", "expected"),
    [
        # Only a minimum: the maximum falls back to 12
        ({"values": {"Main.VolumeLimits": "-60"}}, (-60, 12)),
        # Not a number: both fall back
        ({"values": {"Main.VolumeLimits": "Unknown"}}, (-80, 12)),
        # Empty: both fall back
        ({"values": {"Main.VolumeLimits": ""}}, (-80, 12)),
        # An invalid number makes the whole list invalid
        ({"values": {"Main.VolumeLimits": "-60,twelve"}}, (-80, 12)),
    ],
    indirect=["device_simulation"],
)
async def test_volume_limits_invalid(
    url: str, device_simulation: SimulatedDevice, expected: tuple[int, int]
):
    """An unexpected Main.VolumeLimits doesn't break connecting; the fallback limits are used."""
    device = await NADDevice.async_connect(url)
    assert device.connected
    assert _volume_limits(device) == expected
    await device.async_disconnect()


async def test_volume_limits_invalid_update(
    url: str, device_simulation: SimulatedDevice
):
    """An unexpected update of Main.VolumeLimits doesn't break the connection."""
    device = await NADDevice.async_connect(url)

    device_simulation.send("Main.VolumeLimits=garbage")
    await asyncio.sleep(0.05)

    assert device.connected
    assert _volume_limits(device) == (
        None,
        None,
    )  # No usable limits until the next valid update

    device_simulation.send("Main.VolumeLimits=-40,0")
    device_simulation.send("Main.Volume=-35")
    await asyncio.sleep(0.05)

    assert device.connected
    assert _volume_limits(device) == (-40, 0)
    assert device.volume == -35

    await device.async_disconnect()


def _sources_max(device: NADDevice) -> Any:
    config = device.get_setting_config("Main.Source")
    assert config is not None
    return config.get("max")


async def test_sources_config():
    """Main.Source refers to Main.Sources for its maximum, with 10 as the fallback."""
    settings = (await async_read_device_config(BUILD))["settings"]
    assert settings["Main.Source"]["max"] == ["Main.Sources", 10]
    assert settings["Main.Sources"]["operators"] == "?"


@pytest.mark.simulated_device(values={"Main.Sources": "6", "Main.Source": "1"})
async def test_sources(url: str, device_simulation: SimulatedDevice):
    """The number of sources comes from Main.Sources."""
    device = await NADDevice.async_connect(url)
    assert isinstance(device, NADAmplifier)
    assert _sources_max(device) == 6

    with pytest.raises(NADCommandError):
        await device.async_set_source(7)
    assert await device.async_set_source(6)
    assert device_simulation.get("Main.Source") == "6"

    await device.async_disconnect()


@pytest.mark.simulated_device(values={"Main.Sources": "6", "Main.Source": "1"})
async def test_sources_changed(url: str, device_simulation: SimulatedDevice):
    """A new number of sources reported by the device is used right away."""
    device = await NADDevice.async_connect(url)

    device_simulation.send("Main.Sources=4")
    await asyncio.sleep(0.05)  # Let the reader loop handle the line

    assert _sources_max(device) == 4
    with pytest.raises(NADCommandError):
        await device.async_set_source(5)

    await device.async_disconnect()


@pytest.mark.simulated_device(values={"Main.Sources": "Unknown", "Main.Source": "1"})
async def test_sources_unknown(url: str, device_simulation: SimulatedDevice):
    """Without a number of sources from the device, the fallback of 10 is used."""
    device = await NADDevice.async_connect(url)

    assert _sources_max(device) == 10
    with pytest.raises(NADCommandError):
        await device.async_set_source(11)
    assert await device.async_set_source(10)

    await device.async_disconnect()


@pytest.mark.parametrize("value", [[-50, 6], -50, "-50,6"])
async def test_volume_limits_not_settable(
    url: str, device_simulation: SimulatedDevice, value: Any
):
    """Setting a list, like the volume limits, isn't supported."""
    device = await NADDevice.async_connect(url)
    sent = len(device_simulation.commands)

    with pytest.raises(NADCommandError):
        await device.async_change_setting("Main.VolumeLimits", value)
    assert len(device_simulation.commands) == sent
    assert _volume_limits(device) == (-60, 12)

    await device.async_disconnect()
