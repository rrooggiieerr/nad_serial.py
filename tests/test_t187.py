"""Tests for the NAD T187 surround preamplifier.

Firmware v2.20 of the T187 added and removed settings. From v2.20 it reports its volume
limits, for the main zone and Zone2 to Zone4.
"""

import pytest

from nad_serial import NADDevice, NADMultiZoneReceiver, configs

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


async def test_volume_limits_config():
    """The volume limits come from the device, with the documented limits as the fallback."""
    settings = (await configs.async_read_device_config(BUILD))["settings"]
    assert settings["Main.Volume"]["min"] == ["Main.Volume.Min", -99]
    assert settings["Main.Volume"]["max"] == ["Main.Volume.Max", 19]
    assert settings["Zone2.Volume"]["min"] == ["Zone2.Volume.Min", -99]
    assert settings["Zone2.Volume"]["max"] == ["Zone2.Volume.Max", 19]
    assert settings["Zone3.Volume"]["min"] == ["Zone3.Volume.Min", -99]
    assert settings["Zone3.Volume"]["max"] == ["Zone3.Volume.Max", 19]
    assert settings["Zone4.Volume"]["min"] == ["Zone4.Volume.Min", -99]
    assert settings["Zone4.Volume"]["max"] == ["Zone4.Volume.Max", 19]


@pytest.mark.parametrize(("version", "supported"), [("v2.20", True), ("v2.10", False)])
async def test_volume_limits_firmware(version: str, supported: bool):
    """The device reports its volume limits from firmware v2.20."""
    config = await configs.async_read_device_config(BUILD, version=version)
    settings = config["settings"]
    for setting in (
        "Main.Volume.Min",
        "Main.Volume.Max",
        "Zone2.Volume.Min",
        "Zone2.Volume.Max",
        "Zone3.Volume.Min",
        "Zone3.Volume.Max",
        "Zone4.Volume.Min",
        "Zone4.Volume.Max",
    ):
        assert (setting in settings) is supported, setting


@pytest.mark.simulated_device(
    values={
        "Tuner.Band": "DAB",
        "Tuner.DAB.Service": "Radio 2",
        "Tuner.DAB.DLS": "News",
        "Main.Source": "10",
        "Source10.Enabled": "Yes",
        "Source10.Name": "Tuner",
    }
)
async def test_tuner_content(url: str, device_simulation: SimulatedDevice):
    """On connect the DAB service and text are read, not the settings of other bands."""
    device = await NADDevice.async_connect(url)
    assert isinstance(device, NADMultiZoneReceiver)
    assert device.channel == "Radio 2"
    assert device.title == "News"
    assert not any(
        command.startswith(("Tuner.FM.RDS", "Tuner.XM."))
        for command in device_simulation.commands
    )

    await device.async_disconnect()


@pytest.mark.simulated_device(
    values={
        "Tuner.Band": "DAB",
        "Tuner.DAB.DLS": "News",
        "Main.Source": "1",
        "Source1.Enabled": "Yes",
        "Source1.Name": "CD",
        "Source10.Enabled": "Yes",
        "Source10.Name": "Tuner",
    }
)
async def test_title_other_source(url: str, device_simulation: SimulatedDevice):
    """The tuner's title and channel aren't shown when another source is selected."""
    device = await NADDevice.async_connect(url)
    assert isinstance(device, NADMultiZoneReceiver)
    assert device.title is None
    assert device.channel is None

    await device.async_disconnect()
