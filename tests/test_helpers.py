import pytest

from nad_serial.exceptions import NADCommandError
from nad_serial.helpers import build_command, parse_response, parse_value


def test_parse_response():
    setting, value = parse_response(b"Main.Power=On\n")
    assert setting == "Main.Power"
    assert value == "On"


def test_parse_response_empty_value():
    setting, value = parse_response(b"Prefix.Variable=\n")
    assert setting == "Prefix.Variable"
    assert value == ""


def test_parse_response_string():
    setting, value = parse_response(b"Main.Model=T755\n")
    value = parse_value(setting, value, {"operators": "?", "type": "string"})
    assert setting == "Main.Model"
    assert value == "T755"


def test_parse_response_int():
    setting, value = parse_response(b"Main.Volume=-30\n")
    value = parse_value(setting, value, {"operators": "?", "type": "number"})
    assert setting == "Main.Volume"
    assert value == -30


def test_parse_response_float():
    setting, value = parse_response(b"Tuner.FM.Frequency=87.5\n")
    value = parse_value(setting, value, {"operators": "?", "type": "number"})
    assert setting == "Tuner.FM.Frequency"
    assert value == 87.5


def test_parse_response_none():
    setting, value = parse_response(b"Tuner.FM.Frequency=None\n")
    value = parse_value(setting, value, {"operators": "?", "type": "number"})
    assert setting == "Tuner.FM.Frequency"
    assert value is None


def test_parse_response_unknown():
    setting, value = parse_response(b"Tuner.FM.Frequency=Unknown\n")
    value = parse_value(setting, value, {"operators": "?", "type": "number"})
    assert setting == "Tuner.FM.Frequency"
    assert value is None


def test_parse_response_boolean():
    setting, value = parse_response(b"Main.Power=On\n")
    value = parse_value(
        setting,
        value,
        {"operators": "=+-?", "type": "boolean", "values": ["Off", "On"]},
    )
    assert setting == "Main.Power"
    assert value is True


_BOOLEAN = {"operators": "=?", "type": "boolean", "values": ["Off", "On"]}
_BOOLEAN_LIST = {"operators": "?", "type": "boolean[]", "values": ["Off", "On"]}
_ENUM = {"operators": "=?", "type": "enum", "values": ["None", "PLIIMovie"]}
_NUMBER = {"operators": "=?", "type": "number"}
_NUMBER_LIST = {"operators": "=?", "type": "number[]"}
_STRING = {"operators": "?", "type": "string"}


@pytest.mark.parametrize(
    ("value", "config", "expected"),
    [
        ("-30", _NUMBER, -30),
        ("87.5", _NUMBER, 87.5),
        ("None", _NUMBER, None),
        ("Unknown", _NUMBER, None),
        ("-60,12", _NUMBER_LIST, [-60, 12]),
        ("-60", _NUMBER_LIST, [-60]),
        ("1.5,2", _NUMBER_LIST, [1.5, 2.0]),
        ("None", _NUMBER_LIST, None),
        ("Unknown", _NUMBER_LIST, None),
        ("", _NUMBER, None),
        ("", _NUMBER_LIST, None),
        ("", _BOOLEAN, None),
        ("", _BOOLEAN_LIST, None),
        ("", _ENUM, None),
        ("On", _BOOLEAN, True),
        ("Off", _BOOLEAN, False),
        ("None", _BOOLEAN, None),
        ("Unknown", _BOOLEAN, None),
        ("On,Off", _BOOLEAN_LIST, [True, False]),
        ("On", _BOOLEAN_LIST, [True]),
        ("None", _BOOLEAN_LIST, None),
        ("Unknown", _BOOLEAN_LIST, None),
        ("PLIIMovie", _ENUM, "PLIIMovie"),
        ("None", _ENUM, "None"),  # A value of the enum, not a missing value
        ("T755", _STRING, "T755"),
        ("None", _STRING, "None"),
        ("Unknown", _STRING, "Unknown"),
        ("", _STRING, ""),
    ],
)
def test_parse_value(value, config, expected, caplog):
    """A value is converted to the type of its setting, without warnings."""
    result = parse_value("Main.Setting", value, config)

    assert result == expected
    assert type(result) is type(expected)
    if isinstance(expected, list):
        assert [type(item) for item in result] == [type(item) for item in expected]
    assert not caplog.records


@pytest.mark.parametrize(
    ("value", "config", "expected"),
    [
        ("Loud", _NUMBER, None),
        ("-60,twelve", _NUMBER_LIST, None),
        # The list of values in the config may be incomplete, so the value is kept
        ("PLIIMusic", _ENUM, "PLIIMusic"),
        ("Unknown", _ENUM, "Unknown"),
    ],
)
def test_parse_value_unexpected(value, config, expected, caplog):
    """An unexpected value is reported."""
    assert parse_value("Main.Setting", value, config) == expected
    assert "Please report this" in caplog.text


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
