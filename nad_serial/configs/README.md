# Configuration files

A configuration file tells the NAD Serial library which settings a device model supports and which
values they accept. The library validates each setting and value against the configuration before
sending it.

## File name

When connecting, the library reads the model with `Main.Model?` and loads `<model>.json`. The file
name is the model in lower case, e.g. `t757.json` for a T757.

The configuration is built from these files, each merged over the previous:

1. `device.json`: the settings every device has: power, model and version.
2. `amplifier.json` for an amplifier: volume, mute and source.
3. `tuner.json` for a tuner: band, frequencies and presets.
4. `zones.json` for an amplifier that supports zones.
5. `<model>.json`: the model specific settings.

The model configuration gives the device types, which decide which of `amplifier.json`,
`tuner.json` and `zones.json` are used. When there is no configuration for the model, NAD Serial
detects which device types are supported.

## Format

```json
{
	"device_types": [
		"amplifier",
		"tuner",
		"zones"
	],
	"settings": {
		"Main.Volume": {
			"description": "Set the volume in dB",
			"max": 19,
			"min": -99,
			"operators": "=+-?",
			"type": "number"
		}
	},
	"sends_updates": true
}
```

| Key             | Description                                                                                                                                                          |
| --------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `device_types`  | The device types, `amplifier`, `tuner` and/or `zones`, or `[]` for none. They decide the base configuration files and the class `NADDevice.async_connect()` returns. |
| `settings`      | The supported settings by name, `<Prefix>.<Variable>`, see below.                                                                                                    |
| `sends_updates` | Optional. Whether the device reports changes on its own. When not set, the library detects this.                                                                     |

A setting can have the following keys:

| Key           | Description                                                                                                                                                                                           |
| ------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `type`        | `number`, `boolean`, `enum` or `string`, see below.                                                                                                                                                   |
| `operators`   | The operators the setting accepts, e.g. `=+-?` or `?` for a read-only setting.                                                                                                                        |
| `description` | What the setting does, e.g. from the NAD command list.                                                                                                                                                |
| `min`, `max`  | `number` only. The lowest and highest value. Either a number, or the name of a setting that reports it, e.g. `"max": "Main.Sources"`. That setting is then used.                                      |
| `step`        | `number` only. The value changes in steps of this size, e.g. `0.5`. Either a number, or the name of a setting that reports it, e.g. `"step": "Tuner.AMStep"`. That setting is then used. Default `1`. |
| `values`      | `enum`: the accepted values. `boolean`: the values the device uses for false and true, in that order, e.g. `["Off", "On"]` or `["No", "Yes"]`.                                                        |
| `unit`        | Optional. The unit of the value, e.g. `dB`, `Hz`.                                                                                                                                                     |
| `regex`       | `string` only, optional. A regular expression the whole value must match, e.g. `"0x([0-9A-Fa-f]{2})+"` for a hex code with the `0x` prefix, in pairs of digits.                                       |

| Type      | Values                                                                     |
| --------- | -------------------------------------------------------------------------- |
| `number`  | A number, e.g. `-30` or `0.5`. `None` or `Unknown` are read as no value.   |
| `boolean` | `True` or `False`, sent and read as the two `values`, e.g. `On` and `Off`. |
| `enum`    | One of `values`.                                                           |
| `string`  | Any text.                                                                  |

Setting names and values should be spelled exactly as the device reports them, including case and
spaces. The keys are sorted and the files are indented with tabs, as enforced by the pre-commit
hooks.

### `Main.Volume`

Some devices don't accept `=` for `Main.Volume`, so `amplifier.json` only has `+-?`. For devices
that do, add `"operators": "=+-?"`.

## Inheriting from the base configuration files

The model configuration only needs what differs from `device.json` and the configuration files of
its types:

- Inherited settings can be left out.
- For an inherited setting, only the keys that differ are needed, e.g.
  `"Main.Volume": {"min": -70, "max": 10}`.
- `null` removes an inherited setting or key, e.g. `"Main.Version": null` for a device that doesn't
  report its version, or `"min": null` when changing `Main.Source` from `number` to `enum`.
