# NAD Serial: Python library to control NAD amplifiers, tuners and receivers over serial (RS-232) or Ethernet (telnet)

![Python][python-shield]
[![GitHub Release][releases-shield]][releases]
[![License][license-shield]][license]
[![Maintainer][maintainer-shield]][maintainer]  
[![GitHub Sponsors][github-shield]][github]
[![PayPal][paypal-shield]][paypal]
[![BuyMeCoffee][buymecoffee-shield]][buymecoffee]
[![Patreon][patreon-shield]][patreon]

## Introduction

NAD Serial lets you control **[NAD](https://nadelectronics.com/)** amplifiers, tuners and receivers
over serial (RS-232) or Ethernet (telnet).

## Features

- Asynchronous, built on [serialx](https://github.com/puddly/serialx).
- Connects over serial (RS-232) or Ethernet (telnet).
- Detects the device model and loads the matching configuration.
- Detects the device type for models without configuration.
- Read, set, increment and decrement any supported setting.
- Reads the source names on supported devices.
- Supports zones on multi-zone receivers.

## Supported protocol

If your device follows the second generation NAD protocol (v2.x), it is supported by NAD Serial.
This protocol is used by NAD amplifiers, tuners and receivers with a serial (RS-232) or Ethernet
port.

The binary protocol that some NAD devices, like the D-series, use on TCP port 50001 is not
supported.

The serial and Ethernet commands are identical. All communication is plain ASCII text. Every
command and response has the format:

`<Prefix>.<Variable><Operator><Value>`

The prefix groups related variables, e.g. `Main`, `Zone2`, `Source1` or `Tuner`. Prefix and
variable together name a setting, e.g. `Main.Volume`. Every message is terminated by a carriage
return and/or line feed.

| Operator | Meaning | Example |
|---|---|---|
| `?` | Query the value | `Main.Volume?` |
| `=` | Set the value | `Main.Volume=-30` |
| `+` | Increment or cycle to the next value | `Main.Volume+` |
| `-` | Decrement or cycle to the previous value | `Main.Volume-` |

The device responds with the `=` operator and the resulting value, e.g. `Main.Volume=-30`.

## Supported devices

The following devices are known to work:

**Receivers:**

- T755
- T757

Additionally, NAD Serial includes untested configuration files for the following devices:

**Receivers:**

- T765
- T775
- T777
- T785
- T787

**Surround preamplifiers:**

- M15HD
- T175
- T187

**Amplifiers:**

- C356
- C368
- C388

**Tuners:**

- C427

Other NAD devices that use the [supported protocol](#supported-protocol) should work too, with a
basic set of settings: power, model, version, volume, mute and source.

## Connecting

### USB to serial adapter

If your device has a serial port, use a USB to serial adapter to connect it. See the documentation
of your device for the location of the serial port and how to wire it.

The serial port uses 115200 baud, 8 data bits, no parity, 1 stop bit (8N1) and no flow control.

### Ethernet

If your device has an Ethernet port use a network cable to connect your device to a router.

Use `socket://<ip address>:23` as the URL.

### Serial to Ethernet/WiFi bridge

A serial to Ethernet/WiFi bridge is useful when the device is not close to your computer. Build your
own using an ESP32 and [esp-link](https://github.com/jeelabs/esp-link), or buy an off-the-shelf
product. Configure the bridge for 115200 baud, 8N1.

Use `socket://<ip address>:<port>` or `rfc2217://<ip address>:<port>` as the URL, depending on
which protocol the bridge supports.

### ESPHome Serial Proxy

Install [ESPHome Serial Proxy](https://esphome.io/components/serial_proxy/) on an ESP32 and use
`esphome://<ip address>:<port>/?port_name=<port name>` as the URL.

## Installation

Install NAD Serial with pip:

`pip3 install nad_serial`

## Contribution and appreciation

Do you enjoy using NAD Serial? You can contribute or show your appreciation, in the
following ways.

### Contribute your device model

Is your device supported by NAD Serial but not listed under [Supported devices](#supported-devices)? Let me
know your device model so I can improve the overview of supported devices.

Is there no configuration file for your device model yet, or is the configuration file incomplete or
incorrect? Create a [configuration file](nad_serial/configs/README.md) and submit a pull request
with the new or updated configuration file.

### Star this GitHub page

Help other NAD device users find NAD Serial by starring this GitHub page. Click ⭐ Star on
the top right of the GitHub page.

### Support my work

Please consider supporting my work through one of the following platforms. Your contribution is
greatly appreciated and keeps me motivated:

[![GitHub Sponsors][github-shield]][github]
[![PayPal][paypal-shield]][paypal]
[![BuyMeCoffee][buymecoffee-shield]][buymecoffee]
[![Patreon][patreon-shield]][patreon]

### Hire me

If you're in need of a freelance Python developer for your project please contact me. You can find
my email address on [my GitHub profile](https://github.com/rrooggiieerr).

[python-shield]: https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54
[releases]: https://github.com/rrooggiieerr/nad_serial.py/releases
[releases-shield]: https://img.shields.io/github/v/release/rrooggiieerr/nad_serial.py?style=for-the-badge
[license]: ./LICENSE.md
[license-shield]: https://img.shields.io/github/license/rrooggiieerr/nad_serial.py?style=for-the-badge
[maintainer]: https://github.com/rrooggiieerr
[maintainer-shield]: https://img.shields.io/badge/MAINTAINER-%40rrooggiieerr-41BDF5?style=for-the-badge
[paypal]: https://paypal.me/seekingtheedge
[paypal-shield]: https://img.shields.io/badge/PayPal-00457C?style=for-the-badge&logo=paypal&logoColor=white
[buymecoffee]: https://www.buymeacoffee.com/rrooggiieerr
[buymecoffee-shield]: https://img.shields.io/badge/Buy%20Me%20a%20Coffee-ffdd00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black
[github]: https://github.com/sponsors/rrooggiieerr
[github-shield]: https://img.shields.io/badge/sponsor-30363D?style=for-the-badge&logo=GitHub-Sponsors&logoColor=ea4aaa
[patreon]: https://www.patreon.com/seekingtheedge/creators
[patreon-shield]: https://img.shields.io/badge/Patreon-F96854?style=for-the-badge&logo=patreon&logoColor=white
