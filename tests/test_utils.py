from string import Template

from apitoolbox import utils


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

    payload = {"key": "value", "exp": "fake-date-time"}
    secret = "my_secret"
    utils.jwt_encode(payload, secret)
    assert jwt_encode.call_args == mocker.call(
        payload, secret, algorithm="HS256"
    )
