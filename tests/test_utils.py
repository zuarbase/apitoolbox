import uuid
from datetime import datetime
from string import Template

import jwt
import pytest
import pytz

from apitoolbox import utils


def test_ordered_uuid(mocker):
    ordered_uuid = mocker.patch("apitoolbox.utils.OrderedUUID")

    value = uuid.uuid4()
    result = utils.ordered_uuid(value)
    assert ordered_uuid.call_args == mocker.call(value)
    assert result is ordered_uuid.return_value


def test_ordered_uuid_defaults(mocker):
    ordered_uuid = mocker.patch("apitoolbox.utils.OrderedUUID")

    expected_result = "mock-uuid-1"
    mocker.patch("uuid.uuid1", return_value=expected_result)

    result = utils.ordered_uuid()
    assert ordered_uuid.call_args == mocker.call(expected_result)
    assert result is ordered_uuid.return_value


def test_ordered_uuid_pkg_not_found_error():
    with pytest.raises(RuntimeError) as exc_info:
        utils.ordered_uuid()

    assert str(exc_info.value) == "ordered_uuid package: not found"


def test_render_template():
    template = Template("Say $word.")
    result = utils.render(template, word="hi")
    assert result == "Say hi."


def test_render_template_pass_string():
    template = "<Say $word."
    result = utils.render(template, word="hi")
    assert result == "<Say hi."


def test_render_template_pass_path(mocker):
    mock_open = mocker.mock_open(read_data="Say $word.")
    mocker.patch("builtins.open", mock_open)

    result = utils.render("/path/to/template", word="hi")
    assert result == "Say hi."
    assert mock_open.called


def test_get_session(mocker):
    session = mocker.Mock()

    request = mocker.Mock()
    request.state = mocker.Mock()
    request.state.session = session

    result = utils.get_session(request)
    assert result is session


def test_jwt_encode(mocker):
    jwt_encode = mocker.patch("jwt.encode")

    payload = {
        "key": "value",
        "exp": "fake-date-time"
    }
    secret = "my_secret"
    utils.jwt_encode(payload, secret)
    assert jwt_encode.call_args == mocker.call(
        payload,
        secret,
        algorithm="HS256"
    )


def test_jwt_encode_decode():
    payload = {
        "key": "value",
        "exp": datetime.now(tz=pytz.utc),
    }
    secret = "my_secret"
    result = utils.jwt_encode(payload, secret, "HS256")
    assert result

    decoded_result = jwt.decode(result, secret, "HS256")
    assert decoded_result == payload
