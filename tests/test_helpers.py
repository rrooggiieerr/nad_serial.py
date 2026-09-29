import pytest

from nad_serial.exceptions import NADCommandError
from nad_serial.helpers import build_command, parse_response


def test_parse_response():
    setting, value = parse_response(b"Main.Power=On\n")
    assert setting == "Main.Power"
    assert value == "On"


def test_parse_response_empty_value():
    setting, value = parse_response(b"Prefix.Variable=\n")
    assert setting == "Prefix.Variable"
    assert value == ""


def test_parse_response_string():
    setting, value = parse_response(
        b"Main.Model=T755\n", {"operators": "?", "type": "string"}
    )
    assert setting == "Main.Model"
    assert value == "T755"


def test_parse_response_int():
    setting, value = parse_response(
        b"Main.Volume=-30\n", {"operators": "?", "type": "number"}
    )
    assert setting == "Main.Volume"
    assert value == -30


def test_parse_response_float():
    setting, value = parse_response(
        b"Tuner.FM.Frequency=87.5\n", {"operators": "?", "type": "number"}
    )
    assert setting == "Tuner.FM.Frequency"
    assert value == 87.5


def test_parse_response_none():
    setting, value = parse_response(
        b"Tuner.FM.Frequency=None\n", {"operators": "?", "type": "number"}
    )
    assert setting == "Tuner.FM.Frequency"
    assert value is None


def test_parse_response_unknown():
    setting, value = parse_response(
        b"Tuner.FM.Frequency=Unknown\n", {"operators": "?", "type": "number"}
    )
    assert setting == "Tuner.FM.Frequency"
    assert value is None


def test_parse_response_boolean():
    setting, value = parse_response(
        b"Main.Power=On\n",
        {"operators": "=+-?", "type": "boolean", "values": ["Off", "On"]},
    )
    assert setting == "Main.Power"
    assert value is True


@pytest.mark.parametrize(
    ("setting", "config"),
    [
        ("Main.Model", {"operators": "?", "type": "string"}),
        ("Source1.Name", {"operators": "=?", "type": "string"}),
        (
            "Main.Power",
            {"operators": "=+-?", "type": "boolean", "values": ["Off", "On"]},
        ),
        (
            "Tuner.FM.Mute",
            {"operators": "=+-?", "type": "boolean", "values": ["Off", "On"]},
        ),
    ],
)
def test_build_command_get_setting(setting, config):
    command = build_command(setting, "?", None, config)
    assert command == f"{setting}?"


def test_build_command_get_setting_no_config():
    command = build_command("Main.Model", "?")
    assert command == "Main.Model?"


def test_build_command_set_setting_string():
    command = build_command(
        "Source1.Name", "=", "New name", {"operators": "=+-?", "type": "string"}
    )
    assert command == "Source1.Name=New name"


def test_build_command_set_setting_bool():
    command = build_command(
        "Main.Power",
        "=",
        True,
        {"operators": "=+-?", "type": "boolean", "values": ["Off", "On"]},
    )
    assert command == "Main.Power=On"


@pytest.mark.parametrize(
    "value",
    ["On", "on", "".join(["O", "n"]), "".join(["o", "n"])],  # noqa: FLY002
)
def test_build_command_set_setting_bool_string(value):
    command = build_command(
        "Main.Power",
        "=",
        value,
        {"operators": "=+-?", "type": "boolean", "values": ["Off", "On"]},
    )
    assert command == "Main.Power=On"


def test_build_command_set_setting_bool_invalid_string():
    with pytest.raises(NADCommandError):
        build_command(
            "Main.Power",
            "=",
            "Yes",
            {"operators": "=+-?", "type": "boolean", "values": ["Off", "On"]},
        )


def test_build_command_set_setting_enum():
    command = build_command(
        "Tuner.Band",
        "=",
        "FM",
        {
            "operators": "=+-?",
            "type": "enum",
            "values": ["FM", "AM"],
        },
    )
    assert command == "Tuner.Band=FM"


@pytest.mark.parametrize(
    ("setting", "value", "config", "expected"),
    [
        (
            "Main.Volume",
            5,
            {"operators": "=+-?", "type": "number", "max": 19, "min": -99, "step": 1},
            "5",
        ),
        (
            "Main.Volume",
            5.0,
            {"operators": "=+-?", "type": "number", "max": 19, "min": -99, "step": 1},
            "5",
        ),
        (
            "Main.Volume",
            5.0,
            {"operators": "=+-?", "type": "number", "max": 19, "min": -99},
            "5",
        ),
        (
            "Main.Volume",
            -0,
            {"operators": "=+-?", "type": "number", "max": 19, "min": -99, "step": 1},
            "0",
        ),
        (
            "Main.Volume",
            -5,
            {"operators": "=+-?", "type": "number", "max": 19, "min": -99, "step": 1},
            "-5",
        ),
        (
            "Main.Volume",
            -5.0,
            {"operators": "=+-?", "type": "number", "max": 19, "min": -99, "step": 1},
            "-5",
        ),
        (
            "Main.Volume",
            2.9999999999999996,
            {"operators": "=+-?", "type": "number", "max": 19, "min": -99, "step": 1},
            "3",
        ),
        (
            "Main.DTS.CenterGain",
            0.2,
            {"max": 0.5, "min": 0, "operators": "=+-?", "step": 0.1, "type": "number"},
            "0.2",
        ),
        (
            "Tuner.FM.Frequency",
            102.1,
            {
                "max": 108.0,
                "min": 87.5,
                "operators": "=+-?",
                "step": 0.05,
                "type": "number",
            },
            "102.1",
        ),
        (
            "Tuner.FM.Frequency",
            0.1 + 102,
            {
                "max": 108.0,
                "min": 87.5,
                "operators": "=+-?",
                "step": 0.05,
                "type": "number",
            },
            "102.1",
        ),
    ],
)
def test_build_command_set_setting_number(setting, value, config, expected):
    command = build_command(
        setting,
        "=",
        value,
        config,
    )
    assert command == f"{setting}={expected}"


def test_build_command_set_setting_number_string():
    with pytest.raises(NADCommandError):
        build_command(
            "Main.Volume",
            "=",
            "-30",
            {"operators": "=+-?", "type": "number", "max": 19, "min": -99, "step": 1},
        )


def test_build_command_set_setting_number_bool():
    with pytest.raises(NADCommandError):
        build_command(
            "Main.Volume",
            "=",
            True,
            {"operators": "=+-?", "type": "number", "max": 19, "min": -99, "step": 1},
        )


def test_build_command_set_setting_not_supported():
    with pytest.raises(NADCommandError):
        build_command("Main.Model", "=", "value", {"operators": "?", "type": "string"})


def test_build_command_increase():
    command = build_command(
        "Main.Volume",
        "+",
        None,
        {"operators": "=+-?", "type": "number", "max": 19, "min": -99, "step": 1},
    )
    assert command == "Main.Volume+"


def test_build_command_decrease():
    command = build_command(
        "Main.Volume",
        "-",
        None,
        {"operators": "=+-?", "type": "number", "max": 19, "min": -99, "step": 1},
    )
    assert command == "Main.Volume-"


def test_build_command_toggle():
    command = build_command(
        "Main.Power",
        "+",
        None,
        {"operators": "=+-?", "type": "boolean", "values": ["Off", "On"]},
    )
    assert command == "Main.Power+"


def test_build_command_next():
    command = build_command(
        "Tuner.Band",
        "+",
        None,
        {
            "operators": "=+-?",
            "type": "enum",
            "values": ["FM", "AM"],
        },
    )
    assert command == "Tuner.Band+"


def test_build_command_previous():
    command = build_command(
        "Tuner.Band",
        "-",
        None,
        {
            "operators": "=+-?",
            "type": "enum",
            "values": ["FM", "AM"],
        },
    )
    assert command == "Tuner.Band-"


@pytest.mark.parametrize(
    ("setting", "value", "config"),
    [
        (
            "Source1.Name",
            "New name\rMain.Power=Off",
            {"operators": "=?", "type": "string"},
        ),
        (
            "Main.Power=Off\nSource1.Name=",
            "New name",
            {"operators": "=?", "type": "string"},
        ),
        ("Source1.Name", "é", {"operators": "=?", "type": "string"}),
    ],
)
def test_build_command_set_setting_invalid_characters(setting, value, config):
    with pytest.raises(NADCommandError):
        build_command(setting, "=", value, config)


def test_build_command_invalid_operator():
    with pytest.raises(NADCommandError):
        build_command(
            "Main.Power",
            "^",
            None,
            {"operators": "=+-?", "type": "boolean", "values": ["Off", "On"]},
        )


@pytest.mark.parametrize(
    ("setting", "operator", "value", "config"),
    [
        ("Main.Model", "=", "X000", {"operators": "?", "type": "string"}),
        ("Main.IR", "?", None, {"operators": "=", "type": "number"}),
        ("Source1.Name", "+", None, {"operators": "=?", "type": "string"}),
    ],
)
def test_build_command_unsupported_operator(setting, operator, value, config):
    with pytest.raises(NADCommandError):
        build_command(setting, operator, value, config)


def test_build_command_unsupported_value_type():
    with pytest.raises(NADCommandError):
        build_command("A.B", "=", "value", {"operators": "=+-?", "type": "dict"})


def test_build_command_valid_format():
    command = build_command(
        "Main.IR1",
        "=",
        "0x0000",
        {"operators": "=", "type": "string", "regex": "0x[0-9A-Fa-f]+"},
    )
    assert command == "Main.IR1=0x0000"


@pytest.mark.parametrize(("value"), ["0000", "0x000", "None", 0000])
def test_build_command_invalid_format(value):
    with pytest.raises(NADCommandError):
        build_command(
            "Main.IR1",
            "=",
            value,
            {"operators": "=", "type": "string", "regex": "0x([0-9A-Fa-f]{2})+"},
        )
