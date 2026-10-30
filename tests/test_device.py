"""Tests the NADDevice classes against a simulated device.

Tests that are about the connection run over a serial and over a network connection, with
`@both_transports`. Other tests use a serial connection.
"""

import asyncio

import pytest

from nad_serial import (
    NADAmplifier,
    NADDevice,
    NADMultiZoneAmplifier,
    NADMultiZoneReceiver,
    NADReceiver,
    NADTuner,
)
from nad_serial.exceptions import NADCommandError, NADConnectionError, NADTimeoutError
from nad_serial.helpers import ValueType

from .simulation import SimulatedDevice, async_stop_simulation, both_transports

# A multi-zone receiver with a configuration file
BUILD = "T755_TXX3_DAB"
VALUES = {"Main.Volume": "-30"}


async def _settle() -> None:
    """Lets the reader loop and the simulated device handle what was sent."""
    await asyncio.sleep(0.05)


# Connecting


@both_transports
@pytest.mark.parametrize(
    ("device_simulation", "device_class"),
    [
        ({"build": "T755_TXX3_DAB"}, NADMultiZoneReceiver),
        ({"build": "T778_PG536M_NONE"}, NADMultiZoneAmplifier),
        ({"build": "M15HD_VXP"}, NADMultiZoneAmplifier),
        ({"build": "C368"}, NADAmplifier),
        ({"build": "C427"}, NADTuner),
    ],
    indirect=["device_simulation"],
)
async def test_connect(
    url: str, device_simulation: SimulatedDevice, device_class: type[NADDevice]
):
    """The build decides the class async_connect() returns."""
    device = await NADDevice.async_connect(url)

    assert type(device) is device_class
    assert device.connected
    assert device.build == device_simulation.build
    assert device.model == device_simulation.build.split("_")[0]
    assert device.name == f"NAD {device.model}"
    assert device.is_on

    await device.async_disconnect()
    assert not device.connected


# A device of an unknown model that doesn't report its build or model
_NO_MODEL = {"build": "X000", "values": {"Main.Version": "v1.00", "Main.Volume": "-30"}}


@pytest.mark.simulated_device(**_NO_MODEL)
async def test_connect_build_hint(url: str, device_simulation: SimulatedDevice):
    """A device that doesn't report its build or model is connected with a build hint."""
    device = await NADDevice.async_connect(url, build_hint="X000")

    assert isinstance(device, NADAmplifier)
    assert device.build == "X000"

    await device.async_disconnect()


@pytest.mark.simulated_device(**_NO_MODEL)
async def test_connect_no_build(url: str, device_simulation: SimulatedDevice):
    """Without a build, a model or a build hint, connecting fails."""
    with pytest.raises(NADConnectionError):
        await NADDevice.async_connect(url)


async def test_connect_no_device():
    """Connecting to a serial port that doesn't exist fails."""
    with pytest.raises(NADConnectionError):
        await NADDevice.async_connect("/dev/does-not-exist")


@pytest.mark.parametrize("url", ["network"], indirect=True)
async def test_connect_refused(url: str):
    """Connecting to a network address where nothing listens fails."""
    await async_stop_simulation(url)

    with pytest.raises(NADConnectionError):
        await NADDevice.async_connect(url)


@both_transports
async def test_connect_nothing_answers(url: str):
    """A connection where nothing answers can't be connected to a device."""
    with pytest.raises(NADConnectionError):
        await NADDevice.async_connect(url)


@pytest.mark.parametrize(
    ("device_simulation", "device_types", "device_class"),
    [
        ({"build": "X000", "values": {"Main.Model": "X000"}}, None, NADDevice),
        (
            {"build": "X000", "values": {"Main.Model": "X000", "Main.Volume": "-30"}},
            ["amplifier"],
            NADAmplifier,
        ),
        (
            {"build": "X000", "values": {"Main.Model": "X000", "Tuner.Band": "FM"}},
            ["tuner"],
            NADTuner,
        ),
        (
            {
                "build": "X000",
                "values": {
                    "Main.Model": "X000",
                    "Main.Volume": "-30",
                    "Tuner.Band": "FM",
                },
            },
            ["amplifier", "tuner"],
            NADReceiver,
        ),
        (
            {
                "build": "X000",
                "values": {
                    "Main.Model": "X000",
                    "Main.Volume": "-30",
                    "Zone2.Power": "Off",
                },
            },
            ["amplifier", "zones"],
            NADMultiZoneAmplifier,
        ),
        (
            {
                "build": "X000",
                "values": {
                    "Main.Model": "X000",
                    "Main.Volume": "-30",
                    "Tuner.Band": "FM",
                    "Zone2.Power": "Off",
                },
            },
            ["amplifier", "tuner", "zones"],
            NADMultiZoneReceiver,
        ),
        # Zones without an amplifier
        (
            {"build": "X000", "values": {"Main.Model": "X000", "Zone2.Power": "Off"}},
            ["zones"],
            NADDevice,
        ),
    ],
    indirect=["device_simulation"],
)
async def test_connect_unknown_device(
    url: str,
    device_simulation: SimulatedDevice,
    device_types: list[str] | None,
    device_class: type[NADDevice],
):
    """A model without a configuration file is detected by the settings it answers."""
    device = await NADDevice.async_connect(url)

    assert type(device) is device_class
    assert device.model == "X000"
    assert device._device_config.get("device_types") == device_types
    if device_simulation.get("Main.Volume") is not None:
        assert device.get_setting_value("Main.Volume") == -30
    if device_simulation.get("Tuner.Band") is not None:
        assert isinstance(device, NADTuner)
        assert device.get_band() == "FM"

    await device.async_disconnect()


@pytest.mark.simulated_device(
    build="X000_TXX3_DAB",
    values={
        "Main.Build": "X000_TXX3_DAB",
        "Main.Model": "X000",
        "Main.Volume": "-30",
        "Tuner.Band": "DAB",
    },
)
async def test_connect_unknown_device_with_module(
    url: str, device_simulation: SimulatedDevice
):
    """An unknown model still gets the settings of the known modules in its build."""
    device = await NADDevice.async_connect(url)

    assert type(device) is NADReceiver
    assert device.supports_setting("Tuner.DAB.Service")  # From dab.json
    tuner_band = device.get_setting_config("Tuner.Band")
    assert tuner_band is not None
    assert tuner_band["values"] == ["FM", "AM", "DAB"]
    assert device.get_band() == "DAB"

    await device.async_disconnect()


@pytest.mark.parametrize(
    ("device_simulation", "has_volume_max"),
    [
        ({"build": "T777_PG536M_DAB"}, True),  # The latest firmware, v2.20
        ({"build": "T777_PG536M_DAB", "firmware": "v1.39"}, False),
    ],
    indirect=["device_simulation"],
)
async def test_connect_firmware_version(
    url: str, device_simulation: SimulatedDevice, has_volume_max: bool
):
    """Settings that the firmware version doesn't support are left out."""
    device = await NADDevice.async_connect(url)

    assert device.firmware_version == device_simulation.firmware
    assert device.supports_setting("Main.Volume.Max") is has_volume_max
    assert (device_simulation.get("Main.Volume.Max") is not None) is has_volume_max

    await device.async_disconnect()


# Changing settings


@both_transports
async def test_change_setting(url: str, device_simulation: SimulatedDevice):
    """Changing a setting sends it to the device and returns whether the device took it."""
    device = await NADDevice.async_connect(url)
    assert isinstance(device, NADAmplifier)

    assert await device.async_set_volume(-20)
    assert device.volume == -20
    assert device_simulation.get("Main.Volume") == "-20"

    assert await device.async_mute()
    assert device.muted
    assert device_simulation.get("Main.Mute") == "On"

    await device.async_disconnect()


async def test_turn_off_and_on(url: str, device_simulation: SimulatedDevice):
    """Turning the device off and on changes Main.Power."""
    device = await NADDevice.async_connect(url)

    assert await device.async_turn_off()
    assert not device.is_on
    assert device_simulation.get("Main.Power") == "Off"

    assert await device.async_turn_on()
    assert device.is_on

    await device.async_disconnect()


async def test_increment_and_decrement(url: str, device_simulation: SimulatedDevice):
    """Incrementing and decrementing step a setting."""
    device = await NADDevice.async_connect(url)

    assert await device.async_increment("Main.Volume")
    assert device.get_setting_value("Main.Volume") == -29
    assert await device.async_decrement("Main.Volume")
    assert await device.async_decrement("Main.Volume")
    assert device.get_setting_value("Main.Volume") == -31

    await device.async_disconnect()


async def test_change_unsupported_setting(url: str, device_simulation: SimulatedDevice):
    """A setting the configuration doesn't have can't be changed."""
    device = await NADDevice.async_connect(url)

    with pytest.raises(NADCommandError):
        await device.async_change_setting("Main.DoesNotExist", 1)
    assert not any(
        command.startswith("Main.DoesNotExist")
        for command in device_simulation.commands
    )

    await device.async_disconnect()


async def test_change_invalid_value(url: str, device_simulation: SimulatedDevice):
    """A value the configuration doesn't accept isn't sent to the device."""
    device = await NADDevice.async_connect(url)
    sent = len(device_simulation.commands)

    with pytest.raises(NADCommandError):
        await device.async_change_setting("Main.Volume", 100)  # Above the maximum
    with pytest.raises(NADCommandError):
        await device.async_change_setting("Main.Mute", "Maybe")
    assert len(device_simulation.commands) == sent

    await device.async_disconnect()


# Updates from the device


@both_transports
async def test_update_from_device(url: str, device_simulation: SimulatedDevice):
    """A change on the device itself is stored and passed to the callbacks."""
    device = await NADDevice.async_connect(url)
    updates: list[tuple[str, ValueType | None]] = []
    remove_callback = device.add_callback(
        lambda setting, value: updates.append((setting, value))
    )

    device_simulation.send("Main.Volume=-12")
    await _settle()

    assert updates == [("Main.Volume", -12)]
    assert device.get_setting_value("Main.Volume") == -12
    assert device.sends_updates

    remove_callback()
    device_simulation.send("Main.Volume=-10")
    await _settle()

    assert updates == [("Main.Volume", -12)]  # Not called after removing it
    assert device.get_setting_value("Main.Volume") == -10

    await device.async_disconnect()


async def test_reply_is_not_an_update(url: str, device_simulation: SimulatedDevice):
    """The reply to a command isn't passed to the callbacks; the caller gets the result."""
    device = await NADDevice.async_connect(url)
    updates: list[tuple[str, ValueType | None]] = []
    device.add_callback(lambda setting, value: updates.append((setting, value)))

    assert await device.async_change_setting("Main.Volume", -25)
    await _settle()

    assert updates == []

    await device.async_disconnect()


async def test_callback_exception(url: str, device_simulation: SimulatedDevice):
    """A failing callback doesn't stop the other callbacks or the connection."""
    device = await NADDevice.async_connect(url)
    updates: list[str] = []

    def failing_callback(setting: str, value: ValueType | None) -> None:
        raise RuntimeError("Callback failed")

    device.add_callback(failing_callback)
    device.add_callback(lambda setting, value: updates.append(setting))

    device_simulation.send("Main.Volume=-12")
    await _settle()

    assert updates == ["Main.Volume"]
    assert device.connected

    await device.async_disconnect()


async def test_unknown_setting_from_device(
    url: str, device_simulation: SimulatedDevice
):
    """A setting the configuration doesn't have is stored and passed to the callbacks."""
    device = await NADDevice.async_connect(url)
    updates: list[tuple[str, ValueType | None]] = []
    device.add_callback(lambda setting, value: updates.append((setting, value)))

    device_simulation.send("Main.NewSetting=1")
    device_simulation.send("Main.NewSetting=2")
    await _settle()

    assert updates == [("Main.NewSetting", "1"), ("Main.NewSetting", "2")]
    assert device.get_setting_value("Main.NewSetting") == "2"

    await device.async_disconnect()


# Zones


@pytest.mark.simulated_device(build="T777_PG536M_DAB")
async def test_zones(url: str, device_simulation: SimulatedDevice):
    """A zone controls its own settings on the parent device."""
    device = await NADDevice.async_connect(url)
    assert isinstance(device, NADMultiZoneReceiver)
    assert device.zones is not None
    assert [zone.zone_number for zone in device.zones] == [2, 3, 4]

    zone = device.zones[0]
    assert await zone.async_turn_on()
    assert zone.is_on
    assert device_simulation.get("Zone2.Power") == "On"
    assert zone.get_setting_value("Main.Volume") is None  # Only its own settings

    updates: list[str] = []
    zone.add_callback(lambda setting, value: updates.append(setting))
    device_simulation.send("Main.Volume=-12")
    device_simulation.send("Zone2.Volume=-40")
    await _settle()

    assert updates == ["Zone2.Volume"]
    assert zone.volume == -40

    await device.async_disconnect()


# Losing the connection


@both_transports
async def test_cable_unplugged(url: str, device_simulation: SimulatedDevice):
    """A pulled cable gives timeouts, but the connection stays open."""
    device = await NADDevice.async_connect(url)

    device_simulation.unplug()
    with pytest.raises(NADTimeoutError):
        await device.async_set_volume(-20)
    assert not await device.async_ping()
    assert device.connected

    device_simulation.plug()
    assert await device.async_ping()
    assert await device.async_set_volume(-20)
    assert device_simulation.get("Main.Volume") == "-20"

    await device.async_disconnect()


@both_transports
async def test_connection_lost(url: str, device_simulation: SimulatedDevice):
    """A pulled cable or lost network connection is noticed, and commands fail."""
    device = await NADDevice.async_connect(url)
    assert await device.async_ping()

    device_simulation.disconnect()
    await _settle()

    assert not device.connected
    assert not await device.async_ping()
    with pytest.raises(NADConnectionError):
        await device.async_set_volume(-20)

    await device.async_disconnect()


@both_transports
async def test_connection_lost_while_waiting(
    url: str, device_simulation: SimulatedDevice
):
    """A command waiting for a reply fails when the connection is lost."""
    device = await NADDevice.async_connect(url)

    request = asyncio.create_task(device.async_request_setting("Main.Volume"))
    await asyncio.sleep(0)  # The request is sent, the reply isn't read yet
    device_simulation.disconnect()

    with pytest.raises(NADConnectionError):
        await request
    assert not device.connected

    await device.async_disconnect()


@both_transports
async def test_reconnect(url: str, device_simulation: SimulatedDevice):
    """After disconnecting and reconnecting, changes made in between are read from the device."""
    device = await NADDevice.async_connect(url)
    assert isinstance(device, NADAmplifier)

    await device.async_disconnect()
    device_simulation.set("Main.Volume", "-15")  # Changed while disconnected
    await device.async_reconnect()

    assert device.connected
    assert device.volume == -15
    assert await device.async_set_volume(-20)

    await device.async_disconnect()


@pytest.mark.parametrize("url", ["network"], indirect=True)
async def test_reconnect_after_network_loss(
    url: str, device_simulation: SimulatedDevice
):
    """After the network connection is lost, the device can be reconnected."""
    device = await NADDevice.async_connect(url)
    assert isinstance(device, NADAmplifier)

    device_simulation.disconnect()  # The device keeps listening
    await _settle()
    assert not device.connected

    device_simulation.set("Main.Volume", "-15")
    await device.async_reconnect()

    assert device.connected
    assert device.volume == -15

    await device.async_disconnect()


@pytest.mark.parametrize("url", ["network"], indirect=True)
async def test_reconnect_device_gone(url: str, device_simulation: SimulatedDevice):
    """Reconnecting fails when the device is gone."""
    device = await NADDevice.async_connect(url)

    await device_simulation.async_stop()
    await _settle()

    with pytest.raises(NADConnectionError):
        await device.async_reconnect()
    assert not device.connected


async def test_disconnect(url: str, device_simulation: SimulatedDevice):
    """Disconnecting closes the connection, and commands fail afterwards."""
    device = await NADDevice.async_connect(url)

    await device.async_disconnect()

    assert not device.connected
    with pytest.raises(NADConnectionError):
        await device.async_turn_off()
