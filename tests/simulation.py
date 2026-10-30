"""Simulated connections and a simulated NAD device for the tests.

A simulated connection is reached with the real serialx: `serial_simulation()` creates a
pseudo-terminal, like a device on a USB to serial adapter, and `tcp_simulation()` a TCP server on
127.0.0.1, like a device on the network. Both return the url to connect to. A `SimulatedDevice`
on that url answers the library the way a NAD device of a given build does:

    url = await serial_simulation()  # or tcp_simulation()
    device_simulation = SimulatedDevice(url, "C399", {"Main.VolumeLimits": "-60,12"})
    device = await NADDevice.async_connect(url)

Without a SimulatedDevice, a simulated connection never answers.

The configuration file of the build is assumed to be correct: the device answers every setting
in it. A device of a model without a configuration file answers only the given values.
"""

import asyncio
import contextlib
import os
import re
from typing import Any

import pytest

from nad_serial.configs import async_read_device_config

_COMMAND_RE = re.compile(
    r"(?P<setting>[A-Za-z0-9.]+)(?P<operator>[=+\-?])(?P<value>.*)"
)
_LINE_RE = re.compile(r"[\r\n]")

# Run a test over a serial and over a network connection
both_transports = pytest.mark.parametrize("url", ["serial", "network"], indirect=True)


# Simulated connections


class _Endpoint:
    """The device's end of a simulated connection."""

    def __init__(self) -> None:
        self.device: SimulatedDevice | None = None
        # When unplugged, the connection stays open, but nothing gets through
        self.plugged = True

    def receive(self, data: bytes) -> None:
        """Passes what the library sent to the device, if there is one."""
        if self.device is not None and self.plugged:
            self.device.receive(data.decode("ascii", errors="replace"))

    def write(self, data: str) -> None:
        """Sends data to the library."""
        if self.plugged:
            self._write(data.encode("ascii"))

    def _write(self, data: bytes) -> None:
        raise NotImplementedError

    def disconnect(self) -> None:
        """Drops the connection."""
        raise NotImplementedError

    async def async_stop(self) -> None:
        """Stops the simulated connection."""
        self.disconnect()


class _SerialEndpoint(_Endpoint):
    """The device's end of a pseudo-terminal."""

    def __init__(self) -> None:
        super().__init__()
        import tty  # noqa: PLC0415  # Not available on Windows

        self._master_fd: int | None
        self._slave_fd: int | None
        self._master_fd, self._slave_fd = os.openpty()
        # Raw mode: no echo, and no translation of line endings
        tty.setraw(self._slave_fd)
        os.set_blocking(self._master_fd, False)
        asyncio.get_running_loop().add_reader(self._master_fd, self._on_data)
        self.url = os.ttyname(self._slave_fd)

    def _on_data(self) -> None:
        assert self._master_fd is not None
        try:
            data = os.read(self._master_fd, 4096)
        except BlockingIOError:
            return
        except OSError:
            # The library closed its end
            asyncio.get_running_loop().remove_reader(self._master_fd)
            return
        self.receive(data)

    def _write(self, data: bytes) -> None:
        if self._master_fd is not None:
            with contextlib.suppress(OSError):
                os.write(self._master_fd, data)

    def disconnect(self) -> None:
        """A removed USB to serial adapter: the pseudo-terminal is gone for good."""
        if self._master_fd is not None:
            asyncio.get_running_loop().remove_reader(self._master_fd)
        for fd in (self._master_fd, self._slave_fd):
            if fd is not None:
                with contextlib.suppress(OSError):
                    os.close(fd)
        self._master_fd = self._slave_fd = None


class _NetworkEndpoint(_Endpoint):
    """The device's end of a TCP connection."""

    def __init__(self) -> None:
        super().__init__()
        self._server: asyncio.Server | None = None
        self._writers: set[asyncio.StreamWriter] = set()
        self.url = ""

    async def async_start(self) -> None:
        self._server = await asyncio.start_server(self._handle_client, "127.0.0.1", 0)
        port = self._server.sockets[0].getsockname()[1]
        self.url = f"socket://127.0.0.1:{port}"

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        self._writers.add(writer)
        try:
            while data := await reader.read(4096):
                self.receive(data)
        except ConnectionError:
            pass
        finally:
            self._writers.discard(writer)
            writer.close()

    def _write(self, data: bytes) -> None:
        for writer in self._writers:
            writer.write(data)

    def disconnect(self) -> None:
        """A lost network connection. The device keeps listening, so the library can reconnect."""
        for writer in self._writers:
            writer.close()
        self._writers.clear()

    async def async_stop(self) -> None:
        """The device is gone: the connection is dropped and nothing listens anymore."""
        self.disconnect()
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None


_endpoints: dict[str, _Endpoint] = {}


async def serial_simulation() -> str:
    """Creates a simulated serial connection, and returns its url, e.g. /dev/ttys012."""
    if not hasattr(os, "openpty"):
        pytest.skip("Pseudo-terminals are not supported on this platform")
    endpoint = _SerialEndpoint()
    _endpoints[endpoint.url] = endpoint
    return endpoint.url


async def tcp_simulation() -> str:
    """Creates a simulated network connection, and returns its url, socket://127.0.0.1:<port>."""
    endpoint = _NetworkEndpoint()
    await endpoint.async_start()
    _endpoints[endpoint.url] = endpoint
    return endpoint.url


async def async_stop_simulation(url: str) -> None:
    """Stops a simulated connection: the device is gone."""
    if (endpoint := _endpoints.pop(url, None)) is not None:
        await endpoint.async_stop()


async def async_stop_simulations() -> None:
    """Stops all simulated connections."""
    for url in list(_endpoints):
        await async_stop_simulation(url)


# A simulated device


def _number(value: Any, default: float = 0) -> float:
    """A number from a configuration value, which can also be a reference or a list."""
    if isinstance(value, list):
        value = value[-1]  # The fallback
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value
    return default


def _format_number(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else f"{value:g}"


def default_values(settings: dict[str, dict[str, Any]]) -> dict[str, str]:
    """A plausible value for every setting of a configuration.

    Enums and booleans get their first value, numbers their minimum (or 0), strings an empty
    value. Lists of numbers get no value: a test gives one when it needs it.
    """
    values: dict[str, str] = {}
    for name, config in settings.items():
        setting_type = config.get(
            "type"
        )  # A module can extend a setting without a type
        if setting_type in ("enum", "boolean"):
            values[name] = config["values"][0]
        elif setting_type == "number":
            values[name] = _format_number(_number(config.get("min")))
        elif setting_type == "string":
            values[name] = ""
    return values


class SimulatedDevice:
    """A simulated NAD device of a given build, on a simulated connection.

    Every command for a setting the device knows is answered with `<Setting>=<value>`, and
    commands for settings it doesn't know are ignored. How `+` and `-` change a value follows the
    setting's type in the build's configuration.

    A device of a model with a configuration file knows every setting the configuration has for
    its firmware version, with the values from `default_values()`, updated with `values`. The
    firmware version is the configuration's latest, unless `firmware` gives an older one.

    A device of a model without a configuration file knows only the settings in `values`. It
    doesn't report its build or model unless `values` has them, so it is connected with a
    `build_hint`.
    """

    def __init__(
        self,
        url: str,
        build: str,
        values: dict[str, str] | None = None,
        *,
        firmware: str | None = None,
    ) -> None:
        """Initializes a simulated device on the simulated connection with the url."""
        if (endpoint := _endpoints.get(url)) is None:
            raise ValueError(f"No simulated connection {url}")
        if endpoint.device is not None:
            raise ValueError(f"There already is a simulated device on {url}")
        endpoint.device = self
        self._endpoint = endpoint

        self.url = url
        self.build = build
        self.firmware = firmware
        self._overrides = dict(values or {})
        self._settings: dict[str, dict[str, Any]] = {}
        self._loaded = False
        self._values: dict[str, tuple[str, str]] = {}
        self._loading: asyncio.Task[None] | None = None
        self._pending = ""
        self._received = ""
        # Every command the library sent, for assertions
        self.commands: list[str] = []

    # Test API

    def get(self, setting: str) -> str | None:
        """The value of a setting on the device."""
        if entry := self._values.get(setting.lower()):
            return entry[1]
        return self._overrides.get(setting)

    def set(self, setting: str, value: str) -> None:
        """Changes a value on the device without reporting it, e.g. while disconnected."""
        key = setting.lower()
        if not self._loaded:
            self._overrides[setting] = value
            return
        self._values[key] = (
            self._values[key][0] if key in self._values else setting,
            value,
        )

    def send(self, line: str) -> None:
        """Lets the device report a line on its own, e.g. after using the remote.

        The value of the setting on the device is updated too.
        """
        if (match := _COMMAND_RE.fullmatch(line)) and match["operator"] == "=":
            self.set(match["setting"], match["value"])
        self._endpoint.write(f"{line}\r")

    def disconnect(self) -> None:
        """Drops the connection: a removed USB to serial adapter, or a closed network connection."""
        self._endpoint.disconnect()

    def unplug(self) -> None:
        """Pulls the cable: the connection stays open, but nothing gets through."""
        self._endpoint.plugged = False

    def plug(self) -> None:
        """Plugs the cable back in."""
        self._endpoint.plugged = True

    async def async_stop(self) -> None:
        """Removes the device: the serial port or network address no longer exists."""
        await async_stop_simulation(self.url)

    # Device behaviour

    def receive(self, data: str) -> None:
        """Handles what the library sent. Called by the simulated connection."""
        if not self._loaded:
            # The configuration is still loading, handle the data when it's loaded
            self._pending += data
            if self._loading is None:
                self._loading = asyncio.get_running_loop().create_task(
                    self._async_load()
                )
            return

        *lines, self._received = _LINE_RE.split(self._received + data)
        for line in lines:
            if line:
                self.commands.append(line)
                if (reply := self._answer(line)) is not None:
                    self._endpoint.write(f"{reply}\r")

    async def _async_load(self) -> None:
        """Loads the build's configuration and the device's values."""
        config = await async_read_device_config(self.build)
        if "device_types" not in config:
            # A model without a configuration file knows only the given values
            values = dict(self._overrides)
        else:
            latest = config["settings"].get("Main.Version", {}).get("latest")
            if self.firmware is None:
                self.firmware = latest
            if self.firmware is not None:
                # Only the settings the firmware version supports
                config = await async_read_device_config(
                    self.build, version=self.firmware
                )
            values = default_values(config["settings"])
            values.update(
                {
                    "Main.Build": self.build,
                    "Main.Model": self.build.split("_")[0],
                    "Main.Power": "On",
                }
            )
            if self.firmware is not None:
                values["Main.Version"] = self.firmware
            values.update(self._overrides)

        self._values = {name.lower(): (name, value) for name, value in values.items()}
        self._settings = {
            name.lower(): setting for name, setting in config["settings"].items()
        }
        self._loaded = True

        pending, self._pending = self._pending, ""
        self.receive(pending)

    def _answer(self, command: str) -> str | None:
        """The device's reply to a command, None when it ignores it."""
        match = _COMMAND_RE.fullmatch(command)
        if not match or (key := match["setting"].lower()) not in self._values:
            return None  # A device ignores what it doesn't know

        name, value = self._values[key]
        if match["operator"] == "=":
            value = match["value"]
        elif match["operator"] in "+-":
            value = self._step(self._settings.get(key, {}), value, match["operator"])
        self._values[key] = (name, value)
        return f"{name}={value}"

    @staticmethod
    def _step(config: dict[str, Any], value: str, operator: str) -> str:
        direction = 1 if operator == "+" else -1
        if config.get("type") in ("enum", "boolean"):
            values: list[str] = config["values"]
            index = values.index(value) if value in values else 0
            return values[(index + direction) % len(values)]
        try:
            number = float(value) + direction * _number(config.get("step"), 1)
        except ValueError:
            return value
        if isinstance(config.get("min"), (int, float)):
            number = max(number, config["min"])
        if isinstance(config.get("max"), (int, float)):
            number = min(number, config["max"])
        return _format_number(number)
