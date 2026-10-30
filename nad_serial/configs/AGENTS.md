# Instructions for AI agents: creating a configuration file

These instructions are for an AI agent that creates or updates a device configuration file in this
directory. Read [README.md](README.md) first: it defines the file format, the merge order and the
meaning of every key. This file explains how to get from NAD's documentation to a correct file.

## 1. Gather the facts

- Use the official NAD command list for the model as the only source of settings and values. The
  documents in [`official_documentation`](../../official_documentation) can be read with
  `pdftotext -layout <file>.pdf -`. If the model's document isn't there, ask the user for it.
- Never invent settings, values, ranges or firmware versions. If something is unclear or missing,
  leave it out and tell the user.
- Facts the user observed on a real device (e.g. a reply to `Main.Version?` or a value the device
  sent) take precedence over the documentation. Mention them in your summary.

## 2. Decide which files to change

- Find the build: the user can read it with `Main.Build?`, e.g. `T758_PG536M_DAB`. Devices without
  `Main.Build` report only the model with `Main.Model?`.
- The model file is `<model>.json`, the first part of the build in lower case, e.g. `t758.json`.
- Each further part of the build is a module, e.g. `pg536m.json` or `dab.json`. Settings that only
  exist when a module is installed belong in the module file, not in the model file. Check whether
  the module file already exists before creating one.
- Base files: `device.json`, `amplifier.json`, `tuner.json` and `zones.json`. Don't change them for
  one model. Override what differs in the model file instead.

## 3. Write the model file

- `device_types`: the types the model has, from `amplifier`, `tuner` and `zones`, in that order.
  `zones` only when the document lists `Zone2.*` settings. Use `[]` for a device with none of them.
  Module files never get `device_types`.
- `sends_updates`: only add it when the user knows whether the device reports changes on its own.
- Only add what differs from the base files of its types and its modules:
  - leave out settings that are inherited unchanged;
  - for an inherited setting, only give the keys that differ, e.g. `"Main.Volume": {"min": -70,
    "max": 10}`;
  - use `null` to remove an inherited setting the model doesn't have, or a key that doesn't apply,
    e.g. `"min": null` when changing a `number` into an `enum`.
- Lists are replaced, not merged: when overriding `values`, give the complete list.

## 4. Convert each command from the document

The command list gives, per setting, a name, `Operators`, `Possible Values` and a `Description`.

| In the document | In the configuration |
| --- | --- |
| Setting name, e.g. `Main.Dolby.DRC` | The key, spelled exactly as in the document, including case |
| Setting name with a placeholder, e.g. `SourceX.Enabled` with `1 <= X <= Main.Sources?` | One key per number, e.g. `Source1.Enabled` to `Source10.Enabled`, never `SourceX.Enabled`. See [Numbered settings](#numbered-settings) |
| `Operators: =/+/-/?` | `"operators": "=+-?"`: the operators without slashes, in the order `=+-?`. Allowed: `=+-?`, `=?`, `+-?`, `+-`, `=` or `?` |
| `Range 25 - 100 Step 25` | `"type": "number"`, `"min": 25`, `"max": 100`, `"step": 25`. Leave out `step` when it is 1 |
| Two values that mean off and on, e.g. `On`/`Off` or `Yes`/`No` | `"type": "boolean"`, `"values"` with the false value first: `["Off", "On"]`, `["No", "Yes"]` |
| Any other list of values | `"type": "enum"`, `"values"` with every value spelled exactly as in the document |
| Free text, e.g. a name or a model | `"type": "string"` |
| `Description: ...` | `"description"`: the document's description, without changes |
| A unit in the description, e.g. dB, %, Hz | `"unit"`: `"dB"`, `"%"`, `"Hz"`, `"kHz"`, `"MHz"` |

More rules:

- The document lists enum values in no particular order. Put them in a logical order: the order the
  device steps through them with `+` if known, otherwise from off to on, small to large or low to
  high, e.g. `["Off", "Small", "Large"]`. When a value list for the same setting already exists in
  another model file, use the same order.
- Enum values must be unique, also when ignoring case.
- A `number` setting with both `?` and `+-` needs a `min` and a `max`: the library needs them to
  step to a value. Read-only settings (`?`) don't need a range.
- A `min`, `max` or `step` the device reports through another setting refers to that setting by
  name, e.g. `"max": "Main.Sources"`. When not every firmware has that setting, use a list with the
  documented value as the last item, the fallback: `"max": ["Main.Volume.Max", 19]`. Only the last
  item may be a number, and every name must be a `number` setting in the same configuration.
- A `regex` is only for `string` settings whose value must have a fixed format, e.g. an IR code.

### Numbered settings

Some names in the document contain a placeholder for a number, usually `X`, with its range below the
description:

```
SourceX.Enabled                                    Operators: =/+/-/?
Possible Values:
Yes
No
Description: Enable/disable the source. Example: Source5.Enabled
1 <= X <= Main.Sources?
Example: <CR>SourceX.Enabled=Yes<CR>
```

The device doesn't know `SourceX.Enabled`: `X` stands for a number, and the device only answers to
`Source1.Enabled`, `Source2.Enabled` and so on. So:

- Never write the placeholder in a key. Add one setting for every number in the range, each with the
  same type, operators, values and description, e.g. `Source1.Enabled` to `Source10.Enabled`.
- A fixed range, e.g. `1 <= X <= 5` for `DiracX.Name`, gives exactly those numbers: `Dirac1.Name` to
  `Dirac5.Name`.
- A range that ends in a setting, e.g. `1 <= X <= Main.Sources?`, depends on the device. Use the
  highest value that setting can report: the fallback the configuration already uses for it, e.g.
  the `10` of `"max": ["Main.Sources", 10]` for `Main.Source`. When it isn't known, ask the user.
  The device simply doesn't answer for numbers above its own count.
- Do the same for every setting with that placeholder, e.g. all `SourceX.*` settings, so each number
  has the same set of settings.
- The placeholder also appears in descriptions and examples, e.g. `(see DiracX.State)`. Keep the
  description as in the document.
- Not every `X` is a placeholder: `Tuner.XM.Channel` and the value `SurroundEX` are literal. A
  placeholder is a capital letter directly after a word, in a name with a range like `1 <= X <= 5`.

## 5. Firmware versions

- When a setting is only supported from (or until) a firmware version, add a `firmware` condition,
  e.g. `"firmware": ">=v2.20"` or `"firmware": "<v2.20"`. Write versions as the device reports them,
  with two-digit minor versions: `v2.20`, not `v2.2`.
- Set `"Main.Version": {"latest": "v2.20"}` to the newest firmware version the configuration covers.
  No `firmware` condition may refer to a version after `latest`.
- Only add firmware information that comes from release notes, a document for that version or the
  user's own device.

## 6. Formatting

- Keys are sorted, files are indented with tabs, and every array value is on its own line. This is
  done by the `prettier` pre-commit hook; don't try to format by hand beyond keeping the file valid
  JSON.
- The file name is lower case, letters and digits only, with `.json`.

## 7. Validate

1. Add every build of the model to `BUILDS` in `tests/test_configs.py`, e.g. `"T758_PG536M_DAB"`.
   Without it the new file isn't tested.
2. Run `pytest tests/test_configs.py`. It checks types, operators, ranges, value lists, references,
   firmware conditions and `latest` on the merged configuration of every build.
3. Run `pre-commit run --all-files` to format the files.

## 8. Add the model to the supported devices

Every model with a configuration file is listed under
[Supported devices](../../README.md#supported-devices) in the main README. Always do this for a new
model, it's part of adding the configuration:

- List the model once, by its model name, e.g. `T758`, not per build, and never a module such as
  `PG536M` or `DAB`.
- Put it under "untested configuration files", unless the user confirms it works on their device.
  Then it goes under "The following devices are known to work". When the user later confirms an
  untested model works, move it.
- Put it under the heading of its kind of device as NAD describes it: **Amplifiers**,
  **Receivers**, **Surround preamplifiers** or **Tuners**. Add a heading when none fits, e.g.
  **DACs**. A model is listed under one heading only.
- Keep each list in alphabetical order.
- When updating an existing model, check that it is listed, and add it if not.

## 9. Report back

Summarise for the user:

- which files you created or changed, including where you listed the model in the main README;
- which settings you left out, and why;
- any assumptions, e.g. the order of enum values or a unit you derived from a description;
- any differences between the document and what the user observed on the device.
