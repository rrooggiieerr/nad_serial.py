"""Shared fixtures for the NAD Serial tests."""

from collections.abc import AsyncGenerator

import pytest

from .simulation import (
    SimulatedDevice,
    async_stop_simulations,
    serial_simulation,
    tcp_simulation,
)


@pytest.fixture(autouse=True)
async def stop_simulations() -> AsyncGenerator[None]:
    """Stops the simulations a test created when the test is finished."""
    yield
    await async_stop_simulations()


@pytest.fixture
async def url(request: pytest.FixtureRequest) -> str:
    """The url of a simulated connection, serial unless a test asks for "network".

    Use `@both_transports` from simulation.py to run a test over both.
    """
    if getattr(request, "param", "serial") == "network":
        return await tcp_simulation()
    return await serial_simulation()


@pytest.fixture
def device_simulation(request: pytest.FixtureRequest, url: str) -> SimulatedDevice:
    """A simulated device on the url.

    The device is of the test module's BUILD, with the module's VALUES, if it has them. A test
    changes the device with `@pytest.mark.simulated_device(build=..., values=..., firmware=...)`,
    or with the same keys in a dict through indirect parametrization of `device_simulation`.
    Values are added to the module's VALUES, unless the test gives another build.
    """
    marker = request.node.get_closest_marker("simulated_device")
    options = {**(marker.kwargs if marker else {}), **getattr(request, "param", {})}

    module_build: str | None = getattr(request.module, "BUILD", None)
    build = options.get("build", module_build)
    if build is None:
        raise ValueError(
            "No build for the simulated device: set BUILD or use the marker"
        )
    values: dict[str, str] = {}
    if build == module_build:
        values.update(getattr(request.module, "VALUES", {}))
    values.update(options.get("values", {}))

    return SimulatedDevice(url, build, values, firmware=options.get("firmware"))
