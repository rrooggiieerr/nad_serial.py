"""Tests for the NAD C356 amplifier."""

from nad_serial import configs


async def test_async_read_device_config_amplifier():
    device_config = await configs.async_read_device_config("C368")
    assert device_config["device_types"] == ["amplifier"]
    assert device_config["settings"]["Main.Power"]
    assert device_config["settings"]["Main.Volume"]
    assert "Tuner.Band" not in device_config["settings"]
    assert device_config["settings"]["Main.Sources"]["operators"] == "?"
