# Configuration files

A configuration file tells the NAD Serial library which settings a device model supports and which
values they accept. The library validates each setting and value against the configuration before
sending it.

## Build and file names

When connecting, the library reads the build with `Main.Build?`. Devices that don't support
`Main.Build` are identified with `Main.Model?`. If neither answers, the `build_hint` given to
`NADDevice.async_connect()` is used.

The build is split on `_`, and each part names a configuration file: the part in lower case, letters
and digits only, with `.json` appended. `NONE` parts are ignored, and parts without a configuration
file are skipped. The first part is always the model. Devices without `Main.Build` report just the
model.

For `T758_PG536M_DAB` this becomes:

| Part | File | Contents |
| ---- | ---- | -------- |
| `T758` | `t758.json` | The model |
| `PG536M` | `pg536m.json` | Settings of the PG536M module |
| `DAB` | `dab.json` | The DAB tuner module |

The configuration is built from these files, each merged over the previous:

1. `device.json`: the settings every device has, such as power, model and version.
2. `amplifier.json`, `tuner.json` and/or `zones.json`, depending on the device types.
3. The module files from the build, e.g. `pg536m.json`, `vxp.json`, `dab.json` or `xm.json`.
4. `<model>.json`: the model-specific settings, which override the settings in the device type and
   module files.

The model configuration gives the device types, which decide which files are used in step 2. When
there is no configuration for the model, NAD Serial detects which device types are supported and
still uses the module files from the build.

## Modules

A module file describes hardware that is installed in some builds of a model, such as a video or
HDMI module, or a DAB or XM tuner module. It contains only `settings`, never `device_types`: the
device types come from the model file, or from detection for an unknown model.

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

| Key | Description |
| --- | ----------- |
| `device_types` | The device types, `amplifier`, `tuner` and/or `zones`, or `[]` for a device with none of the device types. They decide the base configuration files and the class `NADDevice.async_connect()` returns. |
| `sends_updates` | Optional. Whether the device reports changes on its own. When not set, the library detects this. |
| `settings` | The supported settings by name, `<Prefix>.<Variable>`, see below. |

A setting can have the following keys:

| Key | Description |
| --- | ----------- |
| `description` | What the setting does, e.g. from the NAD command list. |
| `firmware` | Optional. The firmware versions that support the setting: `>=`, `>`, `=`, `<=`, or `<` and a version, e.g. `">=v2.20"` for a setting added in v2.20, `"<v2.20"` for a setting removed in v2.20, or `"=v1.44"` for a setting of a single version. Without it, the setting applies to all firmware versions. |
| `latest` | Optional, for a setting that reports a version, e.g. `Main.Version` or `DSP.Version`. The latest known version, e.g. `"v2.20"`. |
| `max`, `min` | `number` only. The highest and lowest value. Either a number, the name of a setting that reports it, e.g. `"max": "Main.Sources"`, or a list of these, e.g. `"max": ["Main.Volume.Max", 19]`. See [Values from the device](#values-from-the-device). |
| `operators` | The operators the setting accepts: `=+-?`, `=?`, `+-?`, `+-`, `=` or `?`. |
| `regex` | `string` only, optional. A regular expression the whole value must match, e.g. `"0x([0-9A-Fa-f]{2})+"` for a hex code with the `0x` prefix, in pairs of digits. |
| `step` | `number` only. The value changes in steps of this size, e.g. `0.5`. Either a number, the name of a setting that reports it, e.g. `"step": "Tuner.AMStep"`, or a list of these. See [Values from the device](#values-from-the-device). Default `1`. |
| `type` | `number`, `boolean`, `enum` or `string`, see below. |
| `unit` | Optional. The unit of the value, e.g. `dB`, `Hz`. |
| `values` | `enum`: the accepted values. `boolean`: the values the device uses for false and true, in that order, e.g. `["Off", "On"]` or `["No", "Yes"]`. |

| Type | Values |
| ---- | ------ |
| `boolean` | `True` or `False`, sent and read as the two `values`, e.g. `On` and `Off`. |
| `enum` | One of `values`. |
| `number` | A number, e.g. `-30` or `0.5`. `None` or `Unknown` are read as no value. |
| `string` | Any text. |

Setting names and values should be spelled exactly as the device reports them, including case and
spaces. The keys are sorted and the files are indented with tabs, as enforced by the pre-commit
hooks.

### Values from the device

`max`, `min` and `step` can take their value from the device. Each is one of:

- A number, which is used as is.
- The name of a setting, e.g. `"max": "Main.Sources"`, which gives the value that setting reports.
- A list of these, which are tried in order, e.g. `"max": ["Main.Volume.Max", 19]`. Only the last
  item may be a number. It is the fallback for devices or firmware versions that don't support the
  settings before it.

A setting that is referred to must be a `number` setting of the device. Without a value from the
device or a fallback, `max` and `min` give no limit and `step` is `1`.

### `Main.Volume`

Some devices don't accept `=` for `Main.Volume`, so `amplifier.json` only has `+-?`. For devices
that do, override the `Main.Volume` operators in the model file with `"operators": "=+-?"`.

## Inheriting from the configuration files

The model configuration only needs what differs from `device.json` and the configuration files of
its types and modules:

- Inherited settings can be left out.
- For an inherited setting, only the keys that differ are needed, e.g.
  `"Main.Volume": {"min": -70, "max": 10}`.
- `null` removes an inherited setting or key, e.g. `"Main.Version": null` for a device that doesn't
  report its version, or `"min": null` when changing `Main.Source` from `number` to `enum`.
- Lists are replaced, not merged.

## Adding a model or build

Add `<model>.json`, and a file for each module that has settings of its own. Add the build to
`BUILDS` in `tests/test_configs.py`, and run `pytest tests/test_configs.py` and
`pre-commit run --all-files`. This will validate the configuration files and format the files
according to the pre-commit hooks.
