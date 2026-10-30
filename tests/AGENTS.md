# Instructions for AI agents: writing device specific tests

These instructions are for an AI agent that writes the tests for one device model, in
`tests/test_<model>.py`, e.g. `tests/test_c399.py`. Read
[the configs README](../nad_serial/configs/README.md) first: it explains the configuration files
the tests are about.

## 1. Decide what to test

A device test covers what the model's configuration does differently from the base files
(`device.json`, `amplifier.json`, `tuner.json` and `zones.json`) and its modules. Generic behaviour,
such as connecting, reconnecting or callbacks, is tested in `test_device.py`, and the format of
every configuration file in `test_configs.py`. Don't repeat those. `test_device.py` uses a dummy
configuration, `CONFIGS`, so it doesn't depend on a real model; device tests always use the real
configuration file, as that is what they test.

Read the model's configuration file and look for:

| In the configuration | Test |
| --- | --- |
| `device_types` | The class `NADDevice.async_connect()` returns, e.g. `NADTuner` for a tuner only, and the zones of a multi-zone device |
| `sends_updates` | `device.sends_updates` |
| An overridden `Main.Volume` range or operators | Setting the volume: with `=` it is sent directly, with only `+-` it is stepped, outside the range it is refused |
| A `step` that isn't 1, e.g. `0.5` | Setting and reading a value between whole numbers, through the volume API for `Main.Volume` |
| `Main.Source` as an `enum` | Selecting a source by name, and refusing a number or an unknown name |
| A `min`, `max` or `step` that refers to a setting, e.g. `"max": ["Main.Sources", 10]` | The value comes from the device, follows changes, and the fallback is used when the device has no value |
| A `number[]` or `boolean[]` setting | Reading the list, invalid values, and that changing it is refused |
| `firmware` conditions | A setting supported on one side of the version and not on the other, with the `firmware` option |
| A setting removed with `null`, e.g. `"Main.Version": null` | The device works without it |
| Anything unusual in values, e.g. a version with a capital `V` or a source name with a space | That value read or sent correctly |

Assume the configuration is correct: don't test values or commands the configuration doesn't
define, or situations that haven't been seen on a real device. When the model has nothing that
differs from its base files, it doesn't need a test file.

## 2. Write the test file

Start the file with a docstring that names the model and summarises what is particular about it,
then `BUILD` and `VALUES`:

```python
"""Tests for the NAD C399 amplifier.

The C399 reports its volume limits as one setting with a list of numbers, ...
"""

BUILD = "C399"
VALUES = {"Main.Volume": "-30", "Main.VolumeLimits": "-60,12"}
```

- `BUILD` is a build from `BUILDS` in `test_configs.py`, e.g. `T758_PG536M_DAB`, so the module files
  are included.
- `VALUES` are the values the simulated device starts with, as the device sends them: strings,
  e.g. `"-30"`, `"On"` or `"-60,12"`. The device answers every other setting of its configuration
  with a default: the first value of an enum or boolean, the `min` of a number, or `0` without a
  `min`. Give a realistic value for every setting a test depends on, especially a setting that
  another setting refers to, e.g. `"Main.Sources": "6"`: a default of `0` sources isn't realistic.

Each test connects through the real library and a simulated connection, and disconnects at the
end:

```python
async def test_volume_limits(url: str, device_simulation: SimulatedDevice):
    """The volume limits come from Main.VolumeLimits."""
    device = await NADDevice.async_connect(url)
    assert isinstance(device, NADAmplifier)

    ...

    await device.async_disconnect()
```

- The `url` fixture is a serial connection. Add `@both_transports` from `simulation.py` only when
  the transport matters.
- The `device_simulation` fixture is a `SimulatedDevice` of `BUILD` with `VALUES`. Change it for one
  test with the marker, or for several cases with indirect parametrization:

  ```python
  @pytest.mark.simulated_device(firmware="v2.10", values={"Main.Sources": "4"})

  @pytest.mark.parametrize(
      ("device_simulation", "expected"),
      [({"values": {"Main.VolumeLimits": "-60"}}, (-60, 12)), ({"firmware": "v2.10"}, ...)],
      indirect=["device_simulation"],
  )
  ```

  Values from the marker or parameters are added to `VALUES`. `firmware` sets the firmware version
  the device reports, and leaves out the settings of other firmware versions. Without it, the device
  has the `latest` version of its configuration.
- Every test has a docstring that says what the device does, not how the test works.

## 3. The simulated device

`device_simulation` answers like the real device, and gives the test control over it:

| Use | For |
| --- | --- |
| `device_simulation.get("Main.Volume")` | The value on the device, as a string |
| `device_simulation.set("Main.Volume", "-20")` | Changing a value on the device without telling the library |
| `device_simulation.send("Main.Volume=-20")` | The device reporting a change on its own, e.g. after using the remote |
| `device_simulation.commands` | Every command the library sent, e.g. to check that `Main.Volume=-20` was sent, or that a setting wasn't requested |
| `device_simulation.firmware` | The firmware version the device reports |
| `device_simulation.unplug()`, `plug()` | A pulled cable: nothing gets through, but the connection stays open |
| `device_simulation.disconnect()` | A removed USB to serial adapter, or a closed network connection |
| `await device_simulation.async_stop()` | The device is gone |

The library handles what the device sends in the background, so wait a moment after `send()`, and
after a command the device doesn't answer, e.g. a setting without `?`:

```python
device_simulation.send("Main.Sources=8")
await asyncio.sleep(0.05)  # Let the reader loop handle the line
```

## 4. Test through the public API

Use the API Home Assistant uses: `device.volume`, `async_set_volume()`, `async_set_source()`,
`get_band()` and so on, and `get_setting_config()` or `get_setting_value()` only for settings without
a dedicated method. When the API doesn't support what the configuration allows, e.g. a volume in
steps of 0.5 dB, still write the test against the API. It fails until the library supports it: tell
the user, and don't work around it in the test.

## 5. Validate

1. Run `pytest tests/test_<model>.py`, and `pytest` for all tests.
2. Run `pre-commit run --all-files` to format and check the files.
3. When a test fails, check whether the test or the library is wrong. Don't change the library or the
   configuration to make a test pass: report it to the user.

## 6. Report back

Summarise for the user:

- what you tested for the model, and what you left out, and why;
- tests that fail, and what the library would need to make them pass;
- anything in the configuration that looks wrong.
