"""The NAD Serial library."""

import asyncio
from collections.abc import Callable
import contextlib
import logging
import math
from typing import Any, override

from aenum._enum import property
import serialx
from serialx import SerialException
from serialx.common import Parity, StopBits

from .configs import async_read_device_config
from .exceptions import (
    NADBaseError,
    NADCommandError,
    NADConnectionError,
    NADResponseError,
    NADTimeoutError,
)
from .helpers import (
    REPORT_MESSAGE,
    ValueType,
    build_command,
    parse_response,
    parse_value,
)

with contextlib.suppress(ModuleNotFoundError):
    from ._version import __version__ as __version__


_LINE_ENDINGS = (b"\r", b"\n", b"\x00")

TIMEOUT = 1.0
SETUP_TIMEOUT = 0.5

DEVICE_TYPE_DETECTION_SETTINGS: dict[str, str] = {
    "device": "Main.Model",
    "amplifier": "Main.Volume",
    "tuner": "Tuner.Band",
    "zones": "Zone2.Power",
}

logger = logging.getLogger(__name__)


class NADDevice:
    """A minimal NAD device."""

    # The prefix of the device settings.
    _prefix = "Main"

    # The connection to the device
    _connection: serialx.AsyncSerial
    # The NAD model, e.g. T755
    _model: str | None = None
    _device_type: str = "device"
    # The device configuration
    _device_config: dict[str, Any]

    # The state of the settings
    _setting_states: dict[str, ValueType | None]
    _supported_settings: list[str]

    _callbacks: list[Callable[[str, ValueType | None], None]]

    # Whether the device sends updates on its own.
    _sends_updates: bool | None = None

    _request_lock: asyncio.Lock
    _reader_task: asyncio.Task[None] | None = None
    _pending_request: tuple[str, asyncio.Future[ValueType | None]] | None = None

    def __init__(
        self,
        connection: serialx.AsyncSerial,
        model: str | None,
        device_config: dict[str, Any],
    ):
        """Initializes a NAD device."""
        self._connection = connection
        self._model = model
        self._device_config = device_config
        self._setting_states = {}
        self._supported_settings = []
        self._callbacks = []

        self._request_lock = asyncio.Lock()

    @property
    def connected(self) -> bool:
        """If there is a connection to the device."""
        return self._connection.is_open

    @property
    def model(self) -> str | None:
        """The device model."""
        return self._model

    @property
    def name(self) -> str:
        """The device name."""
        return f"NAD {self._model or self._device_type}"

    @property
    def firmware_version(self) -> str | None:
        """The firmware version."""
        value = self.get_setting_value("Main.Version")
        return str(value) if value else None

    @property
    def serial_number(self) -> str | None:
        """The serial number."""
        value = self.get_setting_value("Main.Serial")
        return str(value) if value else None

    @property
    def sends_updates(self) -> bool:
        """If the device sends updates by itself."""
        return bool(self._sends_updates)

    @property
    def supported_settings(self) -> list[str]:
        """The by the device supported settings."""
        return self._supported_settings

    def supports_setting(self, setting: str) -> bool:
        """Returns True if the given setting is supported."""
        return self.get_setting_config(setting) is not None

    @staticmethod
    async def _async_request_setting_value(
        setting: str, connection: serialx.AsyncSerial
    ) -> ValueType | None:
        command = build_command(setting, "?")
        try:
            # Empty read buffer
            with contextlib.suppress(TimeoutError):
                while True:
                    async with asyncio.timeout(0.05):
                        if not await connection.read(1024):
                            break

            await connection.write(f"\r{command}\r".encode("ascii"))

            async with asyncio.timeout(TIMEOUT):
                while True:
                    try:
                        response = await connection.readuntil(_LINE_ENDINGS)
                    except asyncio.LimitOverrunError as ex:
                        logger.debug("Ignoring %d bytes", ex.consumed)
                        await connection.readexactly(ex.consumed)
                        continue
                    response_setting, response_value = parse_response(response)
                    if response_setting and response_setting.lower() == setting.lower():
                        return response_value
        except TimeoutError:
            return None
        except (OSError, SerialException, asyncio.IncompleteReadError) as ex:
            with contextlib.suppress(OSError, SerialException):
                await connection.close()
            raise NADConnectionError("Disconnected") from ex

    @staticmethod
    async def async_connect(
        url: str,
        *,
        model_hint: str | None = None,
    ) -> NADDevice:
        """Connects to the device and returns one of the NAD device classes."""
        try:
            connection = serialx.async_serial_for_url(
                url,
                baudrate=115200,
                byte_size=8,
                parity=Parity.NONE,
                stopbits=StopBits.ONE,
                write_timeout=TIMEOUT,
                read_timeout=TIMEOUT,
            )
            await connection.open()
        except (OSError, SerialException, ValueError, RuntimeError) as ex:
            raise NADConnectionError(f"Unable to connect to {url}") from ex

        detection_setting = DEVICE_TYPE_DETECTION_SETTINGS["device"]
        model = await NADDevice._async_request_setting_value(
            detection_setting, connection
        )

        if not model:
            model = model_hint

        if not model:
            with contextlib.suppress(OSError, SerialException):
                await connection.close()
            raise NADConnectionError(f"Unable to connect to {url}")

        device_config = None
        if model:
            device_config = await async_read_device_config(model)

        detected_device_types = None
        if not device_config or "device_types" not in device_config:
            detected_device_types = []
            for (
                device_type,
                detection_setting,
            ) in DEVICE_TYPE_DETECTION_SETTINGS.items():
                if device_type == "device":
                    continue

                value = await NADDevice._async_request_setting_value(
                    detection_setting, connection
                )
                if value:
                    detected_device_types.append(device_type)

            device_config = await async_read_device_config(model, detected_device_types)

        if model and detected_device_types is not None:
            logger.warning(
                "No device configuration found for NAD %s with detected device types %s. %s",
                model,
                detected_device_types,
                REPORT_MESSAGE,
            )

        device_types = device_config.get("device_types", [])
        if (
            "zones" in device_types
            and "amplifier" in device_types
            and "tuner" in device_types
        ):
            device = NADMultiZoneReceiver(connection, model, device_config)
        elif "amplifier" in device_types and "tuner" in device_types:
            device = NADReceiver(connection, model, device_config)
        elif "zones" in device_types and "amplifier" in device_types:
            device = NADMultiZoneAmplifier(connection, model, device_config)
        elif "amplifier" in device_types:
            device = NADAmplifier(connection, model, device_config)
        elif "tuner" in device_types:
            device = NADTuner(connection, model, device_config)
        else:
            device = NADDevice(connection, model, device_config)

        try:
            await device._async_setup()
        except NADBaseError:
            await device.async_disconnect()
            raise
        except Exception as ex:
            await device.async_disconnect()
            raise NADConnectionError("Disconnected") from ex

        return device

    async def async_disconnect(self) -> None:
        """Closes the connection."""
        await self._async_stop_reader()

        if self._pending_request is not None and not self._pending_request[1].done():
            self._pending_request[1].set_exception(NADConnectionError("Disconnected"))
            self._pending_request = None

        with contextlib.suppress(OSError, SerialException):
            await self._connection.close()

    async def async_reconnect(self) -> None:
        """Reconnects the connection."""
        await self.async_disconnect()
        try:
            await self._connection.open()
        except (OSError, SerialException, ValueError, RuntimeError) as ex:
            raise NADConnectionError(f"Unable to connect to NAD {self.model}") from ex
        self._start_reader()

        # Read all settings from the device
        await self._async_read_all_settings()

    async def async_ping(self) -> bool:
        """Sends a message to the device to see if the connection is still up."""
        try:
            value = await self.async_request_setting("Main.Power")
        except NADTimeoutError, NADConnectionError:
            pass
        else:
            return value is not None

        return False

    def add_callback(
        self, callback: Callable[[str, ValueType | None], None]
    ) -> Callable[[], None]:
        """Adds a callback."""
        self._callbacks.append(callback)

        def remove_callback() -> None:
            with contextlib.suppress(ValueError):
                self._callbacks.remove(callback)

        return remove_callback

    def _update_callbacks(self, setting: str, value: ValueType | None) -> None:
        for callback in self._callbacks.copy():
            try:
                callback(setting, value)
            except Exception:
                logger.exception("Exception in callback: %s", callback)

    async def _async_read_all_settings(self) -> None:
        """Read all settings from the device."""
        consecutive_response_failures = 0
        for setting, config in self._device_config["settings"].items():
            if "?" in config["operators"]:
                try:
                    async with asyncio.timeout(SETUP_TIMEOUT):
                        value = await self.async_request_setting(setting)
                    consecutive_response_failures = 0
                    self._setting_states[setting.lower()] = value
                except (TimeoutError, NADTimeoutError) as ex:
                    logger.debug("No response for %s", setting)
                    consecutive_response_failures += 1
                    if consecutive_response_failures >= 5:
                        raise NADConnectionError("No response") from ex

    async def _async_setup(self) -> None:
        """Setup the NAD device."""
        self._sends_updates = self._device_config.get("sends_updates")

        self._supported_settings = list(self._device_config["settings"].keys())

        # Lowercase the setting names
        self._device_config["settings"] = {
            setting.lower(): config
            for setting, config in self._device_config["settings"].items()
        }

        # Start the reader
        self._start_reader()

        # Read all settings from the device
        await self._async_read_all_settings()

        # Resolve links to setting states in _device_settings
        for config in self._device_config["settings"].values():
            for key in ("min", "max", "step"):
                if isinstance(config.get(key), str):
                    value = self.get_setting_value(config.get(key))
                    if isinstance(value, (int, float)) and not isinstance(value, bool):
                        config[key] = value
                    else:
                        del config[key]

    def get_setting_config(self, setting: str) -> dict[str, Any] | None:
        """Gets the configuration for a setting."""
        return self._device_config["settings"].get(setting.lower())

    def get_setting_value(self, setting: str) -> ValueType | None:
        """Gets the value of a setting from the setting state dict."""
        return self._setting_states.get(setting.lower())

    def _parse_response(self, response: bytes) -> tuple[str | None, ValueType | None]:
        setting, value = parse_response(response)
        if setting is None:
            return None, None
        if (setting_config := self.get_setting_config(setting)) is None:
            return setting, value
        return setting, parse_value(setting, value, setting_config)

    async def _reader_loop(self) -> None:
        """Reads all data sent by the device."""
        try:
            while True:
                try:
                    response = await self._connection.readuntil(_LINE_ENDINGS)
                except TimeoutError:
                    continue
                except asyncio.IncompleteReadError as ex:
                    raise NADConnectionError("Connection closed by device") from ex
                except asyncio.LimitOverrunError as ex:
                    logger.debug("Ignoring %d bytes", ex.consumed)
                    await self._connection.readexactly(ex.consumed)
                    continue

                if not (response := response.strip(b" \t\r\n\x00")):
                    continue

                logger.debug("Received %s", response)
                setting, value = self._parse_response(response)
                if not setting:
                    continue

                setting_lc = setting.lower()
                if setting_lc in self._device_config["settings"]:
                    self._setting_states[setting_lc] = value

                if (
                    self._pending_request
                    and self._pending_request[0] == setting_lc
                    and not self._pending_request[1].done()
                ):
                    # Response to a request
                    self._pending_request[1].set_result(value)
                    continue

                if not (
                    self._pending_request and self._pending_request[0] == setting_lc
                ):
                    # Device-initiated updates
                    if self._sends_updates is None:
                        logger.warning(
                            "The NAD %s reports changes on its own, but its configuration doesn't say so. %s",
                            self.model,
                            REPORT_MESSAGE,
                        )
                        self._sends_updates = True

                    if (
                        setting_lc not in self._device_config["settings"]
                        and setting_lc not in self._setting_states
                    ):
                        self._setting_states[setting_lc] = value
                        logger.warning(
                            "The NAD %s reported a new setting %s that is not in its configuration. %s",
                            self.model,
                            setting,
                            REPORT_MESSAGE,
                        )

                self._update_callbacks(setting, value)
        except asyncio.CancelledError:
            raise
        except Exception as ex:
            logger.exception("Connection to NAD %s lost", self.model)

            if (
                self._pending_request is not None
                and not self._pending_request[1].done()
            ):
                self._pending_request[1].set_exception(
                    ex if isinstance(ex, NADBaseError) else NADConnectionError(str(ex))
                )
                self._pending_request = None

            with contextlib.suppress(OSError, SerialException):
                await self._connection.close()

    def _start_reader(self) -> None:
        if self._reader_task is None or self._reader_task.done():
            self._reader_task = asyncio.create_task(
                self._reader_loop(), name=f"NAD {self.model} reader"
            )

    async def _async_stop_reader(self) -> None:
        task, self._reader_task = self._reader_task, None
        if task is not None:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    async def _async_request(
        self,
        setting: str,
        operator: str,
        value: ValueType | None = None,
        setting_config: dict[str, Any] | None = None,
    ) -> ValueType | None:
        """Sends a request and waits for the response."""
        if not self.connected:
            raise NADConnectionError("Not connected")

        if not setting_config:
            if not self.supports_setting(setting):
                return None

            setting_config = self.get_setting_config(setting)

        command = build_command(setting, operator, value, setting_config)
        request = f"\r{command}\r"

        async with self._request_lock:
            loop = asyncio.get_running_loop()
            future = loop.create_future()

            logger.debug("Sending %s", request.strip())
            try:
                # The connection can be lost while waiting for the lock.
                if not self.connected:
                    raise NADConnectionError("Not connected")
                self._pending_request = (setting.lower(), future)
                await self._connection.write(request.encode("ascii"))
                return await asyncio.wait_for(future, TIMEOUT)
            except TimeoutError as ex:
                raise NADTimeoutError(
                    f"No response from device on {request.strip()}"
                ) from ex
            except (OSError, SerialException) as ex:
                with contextlib.suppress(OSError, SerialException):
                    await self._connection.close()
                raise NADConnectionError(f"Unable to send {request.strip()}") from ex
            finally:
                if (
                    self._pending_request is not None
                    and self._pending_request[1] is future
                ):
                    self._pending_request = None

    async def async_request_setting(self, setting: str) -> ValueType | None:
        """Gets the value of a setting from the device."""
        return await self._async_request(setting, "?")

    async def async_change_setting(self, setting: str, value: ValueType) -> bool:
        """Change a setting."""
        if not (setting_config := self.get_setting_config(setting)):
            raise NADCommandError(
                f"Setting {setting} is not supported by NAD {self.model}"
            )
        if (
            setting_config["type"] != "number"
            and "=" not in setting_config["operators"]
        ):
            raise NADCommandError(f"Changing {setting} not allowed")
        if setting_config["type"] == "number" and setting_config["operators"] == "?":
            raise NADCommandError(f"Changing {setting} not allowed")
        if (
            setting_config["type"] == "number"
            and "=" not in setting_config["operators"]
            and "?" not in setting_config["operators"]
        ):
            # We can't step to the value if we can't know the current value.
            raise NADCommandError(f"Changing {setting} not possible")
        if setting_config["type"] == "number":
            minimum = setting_config.get("min")
            maximum = setting_config.get("max")
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise NADCommandError(f"{value} not a number")
            if "=" not in setting_config["operators"] and (
                (minimum is not None and value < minimum)
                or (maximum is not None and value > maximum)
            ):
                raise NADCommandError(f"{value} out of range {minimum} - {maximum}")
        if setting_config["type"] == "boolean" and not isinstance(value, bool):
            raise NADCommandError(f"{value} not a boolean")

        if (
            setting_config["type"] == "number"
            and "=" not in setting_config["operators"]
        ):
            # Numerical can not directly be set but needs to be stepped to.
            current_value = self.get_setting_value(setting)
            if current_value is None:
                raise NADResponseError("Invalid current value")
            if current_value == value:
                return True

            step = setting_config.get("step", 1)
            direction = "+" if current_value < value else "-"
            needed_steps = math.ceil(abs(value - current_value) / step)
            for _ in range(needed_steps + 1):
                current_value = await self._async_request(setting, direction, None)
                if current_value is None:
                    raise NADResponseError("Unexpected response")
                if current_value == value:
                    break
                if direction == "+" and current_value > value:
                    break
                if direction == "-" and current_value < value:
                    break
        else:
            current_value = await self._async_request(setting, "=", value)

        self._setting_states[setting.lower()] = current_value

        if setting_config["type"] == "number":
            return isinstance(current_value, (int, float)) and math.isclose(
                current_value, value, abs_tol=1e-9
            )
        if setting_config["type"] == "enum" and isinstance(value, str):
            return (
                isinstance(current_value, str)
                and current_value.lower() == value.lower()
            )
        return current_value == value

    async def _async_step(self, setting: str, operator: str) -> bool:
        current_value = self.get_setting_value(setting)
        new_value = await self._async_request(setting, operator)

        self._setting_states[setting.lower()] = new_value

        return current_value != new_value

    async def async_increment(self, setting: str) -> bool:
        """Increments a setting."""
        if not (setting_config := self.get_setting_config(setting)):
            raise NADCommandError(
                f"Setting {setting} is not supported by NAD {self.model}"
            )
        if "+" not in setting_config["operators"]:
            raise NADCommandError(f"Incrementing {setting} not allowed")

        return await self._async_step(setting, "+")

    async def async_decrement(self, setting: str) -> bool:
        """Decrements a setting."""
        if not (setting_config := self.get_setting_config(setting)):
            raise NADCommandError(
                f"Setting {setting} is not supported by NAD {self.model}"
            )
        if "-" not in setting_config["operators"]:
            raise NADCommandError(f"Decrementing {setting} not allowed")

        return await self._async_step(setting, "-")

    @property
    def is_on(self) -> bool:
        """If the device is on."""
        return self.get_setting_value(f"{self._prefix}.Power") is True

    async def async_request_is_on(self) -> bool:
        """Gets the value of a setting from the device."""
        return await self.async_request_setting(f"{self._prefix}.Power") is True

    async def async_turn_on(self) -> bool:
        """Turns the device on."""
        return await self.async_change_setting(f"{self._prefix}.Power", True)

    async def async_turn_off(self) -> bool:
        """Turns the device off."""
        return await self.async_change_setting(f"{self._prefix}.Power", False)


class NADAmplifier(NADDevice):
    """A NAD amplifier."""

    _device_type: str = "amplifier"

    @override
    async def _async_setup(self) -> None:
        """Setup the NAD amplifier."""
        await super()._async_setup()

        source_config = self.get_setting_config(f"{self._prefix}.Source")
        if (
            not source_config
            or source_config["type"] != "number"
            or self.supports_setting("Source1.Name")
        ):
            return

        # Try to get the source names, even though the device does not specify the needed settings.
        for i in range(1, 11):
            try:
                setting = f"Source{i}.Name"
                name_config = {"operators": "?", "type": "string"}
                async with asyncio.timeout(SETUP_TIMEOUT):
                    value = await self._async_request(
                        setting,
                        "?",
                        setting_config=name_config,
                    )
                if value is None:
                    break
                self._supported_settings.append(setting)
                self._device_config["settings"][setting.lower()] = name_config.copy()
                self._setting_states[setting.lower()] = value

                setting = f"Source{i}.Enabled"
                enabled_config = {
                    "operators": "?",
                    "type": "boolean",
                    "values": ["No", "Yes"],
                }
                if not self.supports_setting(setting):
                    with contextlib.suppress(TimeoutError, NADTimeoutError):
                        async with asyncio.timeout(SETUP_TIMEOUT):
                            value = await self._async_request(
                                setting, "?", setting_config=enabled_config
                            )
                        if value is not None:
                            self._supported_settings.append(setting)
                            self._device_config["settings"][setting.lower()] = (
                                enabled_config.copy()
                            )
                            self._setting_states[setting.lower()] = value == "Yes"
            except TimeoutError, NADTimeoutError:
                break

    @property
    def volume(self) -> int | None:
        """Gets the amplifier volume in dB."""
        value = self.get_setting_value(f"{self._prefix}.Volume")
        return value if isinstance(value, int) and not isinstance(value, bool) else None

    async def async_request_volume(self) -> int | None:
        """Gets the value of a setting from the device."""
        value = await self.async_request_setting(f"{self._prefix}.Volume")
        return value if isinstance(value, int) and not isinstance(value, bool) else None

    @property
    def muted(self) -> bool | None:
        """Gets the amplifier mute state."""
        value = self.get_setting_value(f"{self._prefix}.Mute")
        return value if isinstance(value, bool) else None

    async def async_request_mute(self) -> bool | None:
        """Gets the value of a setting from the device."""
        value = await self.async_request_setting(f"{self._prefix}.Mute")
        return value if isinstance(value, bool) else None

    @property
    def source_names(self) -> dict[int | str, str] | None:
        """The source names by source, None if they are not known."""
        source_config = self.get_setting_config(f"{self._prefix}.Source")
        if source_config and source_config["type"] == "enum":
            return {source_name: source_name for source_name in source_config["values"]}

        source_names = {}
        for i in range(1, 11):
            if self.get_setting_value(f"Source{i}.Enabled") is False:
                continue
            if value := self.get_setting_value(f"Source{i}.Name"):
                source_names[i] = value

        return source_names or None

    @property
    def source_name(self) -> str | None:
        """The name of the current source, if known."""
        source_config = self.get_setting_config(f"{self._prefix}.Source")
        if not source_config:
            return None

        source = self.get_setting_value(f"{self._prefix}.Source")

        if (
            isinstance(source, int)
            and source_config["type"] == "number"
            and self.source_names
        ):
            return self.source_names.get(source)

        if source_config["type"] == "enum" and source in source_config["values"]:
            return source

        return None

    async def async_request_source_name(self) -> ValueType | None:
        """Gets the source name from the device."""
        source_config = self.get_setting_config(f"{self._prefix}.Source")
        if not source_config:
            return None

        source = await self.async_request_setting(f"{self._prefix}.Source")

        if (
            isinstance(source, int)
            and source_config["type"] == "number"
            and self.source_names
        ):
            return self.source_names.get(source)

        if source_config["type"] == "enum" and source in source_config["values"]:
            return source

        return None

    async def async_set_volume(self, volume: int) -> bool:
        """Sets the amplifier volume."""
        return await self.async_change_setting(f"{self._prefix}.Volume", volume)

    async def async_mute(self) -> bool:
        """Mutes the amplifier."""
        return await self.async_change_setting(f"{self._prefix}.Mute", True)

    async def async_unmute(self) -> bool:
        """Unmutes the amplifier."""
        return await self.async_change_setting(f"{self._prefix}.Mute", False)

    async def async_set_source(self, source: int | str) -> bool:
        """Sets the source."""
        return await self.async_change_setting(f"{self._prefix}.Source", source)


class NADMultiZoneAmplifier(NADAmplifier):
    """A multi-zone NAD amplifier."""

    _zones: list[NADZone] | None = None

    @override
    async def _async_setup(self) -> None:
        """Setup the multi-zone NAD amplifier."""
        await super()._async_setup()

        zones = []
        for i in range(2, 5):
            setting_config = self.get_setting_config(f"zone{i}.power")
            if setting_config is not None:
                zones.append(NADZone(self, i))

        if zones:
            self._zones = zones

    @property
    def zones(self) -> list[NADZone] | None:
        """Returns the zones of the amplifier."""
        return self._zones


class NADZone(NADAmplifier):
    """A zone."""

    _parent_device: NADMultiZoneAmplifier
    _zone_number: int

    def __init__(self, parent_device: NADMultiZoneAmplifier, zone_number: int):  # pylint: disable=super-init-not-called
        """Initializes an amplifier zone."""
        self._parent_device = parent_device
        self._zone_number = zone_number
        self._prefix = f"Zone{zone_number}"

    @property
    @override
    def _setting_states(self):
        return {
            setting: state
            for setting, state in self._parent_device._setting_states.items()  # noqa: SLF001
            if setting.startswith(f"{self._prefix.lower()}.")
        }

    @property
    @override
    def connected(self) -> bool:
        """If there is a connection to the zone."""
        return self._parent_device.connected

    @property
    @override
    def model(self) -> str | None:
        """The device model."""
        return self._parent_device.model

    @property
    def zone_number(self) -> int:
        """The zone number."""
        return self._zone_number

    @property
    @override
    def name(self) -> str:
        """The zone name."""
        return f"NAD {self.model} Zone {self.zone_number}"

    @property
    @override
    def supported_settings(self) -> list[str]:
        """The by the device supported settings."""
        return [
            setting
            for setting in self._parent_device._supported_settings  # noqa: SLF001
            if setting.lower().startswith(f"{self._prefix.lower()}.")
        ]

    @property
    @override
    def source_names(self) -> dict[int | str, str] | None:
        """The source names by source, None if they are not known."""
        return self._parent_device.source_names

    @override
    def add_callback(
        self, callback: Callable[[str, ValueType | None], None]
    ) -> Callable[[], None]:
        """Adds a callback."""

        def zone_callback(setting: str, value: ValueType | None) -> None:
            if setting.lower().startswith((f"{self._prefix.lower()}.", "source")):
                callback(setting, value)

        return self._parent_device.add_callback(zone_callback)

    @override
    def get_setting_config(self, setting: str) -> dict[str, Any] | None:
        """Gets the configuration for a setting."""
        if not setting.lower().startswith(f"{self._prefix.lower()}."):
            return None
        return self._parent_device.get_setting_config(setting)

    @override
    def get_setting_value(self, setting: str) -> ValueType | None:
        """Gets the state of a setting."""
        if not setting.lower().startswith(f"{self._prefix.lower()}."):
            return None
        return self._parent_device.get_setting_value(setting)

    @override
    async def _async_request(
        self,
        setting: str,
        operator: str,
        value: ValueType | None = None,
        setting_config: dict[str, Any] | None = None,
    ) -> ValueType | None:
        """Sends a request and waits for the response."""
        return await self._parent_device._async_request(  # noqa: SLF001
            setting, operator, value, setting_config
        )


class NADTuner(NADDevice):
    """A NAD tuner."""

    _device_type: str = "tuner"

    def get_band(self) -> str | None:
        """Gets the tuner band."""
        value = self.get_setting_value("Tuner.Band")
        return str(value) if value else None

    async def async_set_band(self, band: str) -> bool:
        """Selects the tuner band."""
        return await self.async_change_setting("Tuner.Band", band)

    def get_am_frequency(self) -> int | None:
        """Gets the AM frequency."""
        value = self.get_setting_value("Tuner.AM.Frequency")
        return int(value) if value is not None else None

    async def async_set_am_frequency(self, frequency: int) -> bool:
        """Tunes to an AM frequency."""
        return await self.async_change_setting("Tuner.AM.Frequency", frequency)

    def get_fm_frequency(self) -> float | None:
        """Gets the FM frequency."""
        value = self.get_setting_value("Tuner.FM.Frequency")
        return float(value) if value is not None else None

    async def async_set_fm_frequency(self, frequency: float) -> bool:
        """Tunes to an FM frequency."""
        return await self.async_change_setting("Tuner.FM.Frequency", frequency)

    def get_preset(self) -> int | None:
        """Gets the current preset."""
        value = self.get_setting_value("Tuner.Preset")
        return int(value) if value is not None else None

    async def async_set_preset(self, preset: int) -> bool:
        """Selects a tuner preset."""
        return await self.async_change_setting("Tuner.Preset", preset)

    def get_fm_rdsname(self) -> str | None:
        """Gets the RDS name."""
        value = self.get_setting_value("Tuner.FM.RDSName")
        return str(value) if value else None

    def get_fm_rdstext(self) -> str | None:
        """Gets the RDS text."""
        value = self.get_setting_value("Tuner.FM.RDSText")
        return str(value) if value else None


class NADReceiver(NADAmplifier, NADTuner):
    """A NAD device with an amplifier and a tuner."""

    _device_type: str = "receiver"


class NADMultiZoneReceiver(NADMultiZoneAmplifier, NADTuner):
    """A NAD device with a multi-zone amplifier and a tuner."""

    _device_type: str = "receiver"
