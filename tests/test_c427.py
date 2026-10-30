"""Tests for the NAD C427 tuner.

The C427 is a tuner only, without an amplifier, and reports the RDS name and text of FM
stations.
"""

import asyncio

from nad_serial import NADDevice, NADTuner, configs

from .simulation import SimulatedDevice

BUILD = "C427"
VALUES = {
    "Tuner.Band": "FM",
    "Tuner.FM.Frequency": "98.5",
    "Tuner.FM.RDSName": "Radio 2",
    "Tuner.FM.RDSText": "News",
}


async def test_async_read_device_config_c427():
    device_config = await configs.async_read_device_config("C427")
    assert device_config["device_types"] == ["tuner"]


async def test_device_class(url: str, device_simulation: SimulatedDevice):
    """The C427 is a tuner without an amplifier."""
    device = await NADDevice.async_connect(url)
    assert type(device) is NADTuner

    await device.async_disconnect()


async def test_rds(url: str, device_simulation: SimulatedDevice):
    """The RDS name and text of the FM station are read, and follow changes."""
    device = await NADDevice.async_connect(url)
    assert isinstance(device, NADTuner)

    await device.async_request_settings(("Tuner.FM.RDSName", "Tuner.FM.RDSText"))
    assert device.get_fm_frequency() == 98.5
    assert device.get_fm_rdsname() == "Radio 2"
    assert device.get_fm_rdstext() == "News"

    device_simulation.send("Tuner.FM.RDSText=Weather")
    await asyncio.sleep(0.05)  # Let the reader loop handle the line
    assert device.get_fm_rdstext() == "Weather"

    await device.async_disconnect()
