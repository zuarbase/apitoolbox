import uuid
from string import Template

import pytest
from sqlalchemy.engine.url import make_url

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


@pytest.mark.parametrize("url,input_kw, actual_kw", [
    ("postgres://localhost/my_db", {}, {"pool_pre_ping": True}),
    ("postgres://localhost/my_db",
     {"pool_pre_ping": False, "echo": True},
     {"pool_pre_ping": False, "echo": True}),
    ("snowflake://localhost/my_db",
     {},
     {
         "pool_pre_ping": False,
         "pool_reset_on_return": None,
         "_initialize": False
     }),
    ("snowflake://localhost/my_db",
     {
         "pool_pre_ping": True,
         "echo": True,
     },
     {
         "pool_pre_ping": True,
         "echo": True,
         "pool_reset_on_return": None,
         "_initialize": False
     }),
], ids=[
    "postgres_default_kw",
    "postgres_custom_kw",
    "snowflake_default_kw",
    "snowflake_custom_kw",
])
def test_create_engine(mocker, url, input_kw, actual_kw):
    """Test `create_engine` parameters for different databases."""
    create_engine = mocker.patch("sqlalchemy.create_engine")

    engine = utils.create_engine(url, **input_kw)
    assert engine == create_engine.return_value
    assert create_engine.call_args == mocker.call(
        make_url(url),
        **actual_kw
    )


def test_create_engine__snowflake_ignore_case(mocker):
    create_engine = mocker.patch("sqlalchemy.create_engine")

    # Test - not called for others
    url = "postgres://localhost/my_db"
    engine = utils.create_engine(url)
    assert engine == create_engine.return_value
    assert not engine.execute.called

    # Test - called for snowflake
    url = "snowflake://localhost/my_db"
    engine = utils.create_engine(url)
    assert engine == create_engine.return_value
    assert engine.execute.call_args == mocker.call(
        "alter session set quoted_identifiers_ignore_case = true;"
    )
