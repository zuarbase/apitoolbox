from datetime import datetime

import fastapi
from itsdangerous import URLSafeTimedSerializer

from apitoolbox import endpoints, models

SENDER = "user@test.com"
BASE_URL = "http://localhost"


class User(
    models.User, models.mixins.ConfirmationMixin, models.mixins.DictMixin
):
    __tablename__ = "test_register_users"
    __model_mapping__ = False


def test_register_get(session, app, client):
    endpoint = endpoints.RegisterEndpoint(
        User,
        secret="s0secret",
        form_template="<html>${title}</html>",
    )

    @app.get("/register")
    async def _get():
        return await endpoint.on_get()

    res = client.get("/register")
    assert res.status_code == 200
    assert res.text == "<html>APIToolbox</html>"


def test_register_post(session, app, client, mocker):
    endpoint = endpoints.RegisterEndpoint(
        User,
        secret="s0secret",
        sender=SENDER,
        sent_template="<html>${email}</html>",
    )
    mocker.patch.object(endpoint, "send_email_confirmation")

    @app.post("/register")
    async def _post(
        username: str = fastapi.Form(None),
        password: str = fastapi.Form(None),
        email: str = fastapi.Form(None),
    ):
        return await endpoint.on_post(
            BASE_URL,
            session,
            username=username,
            password=password,
            email=email,
        )

    recipient = "recipient@test.com"
    res = client.post(
        "/register",
        data={
            "username": "testuser",
            "password": "passw0rd",
            "email": recipient,
        },
    )
    assert res.status_code == 200
    assert res.text == f"<html>{recipient}</html>"


def test_register_post_password_not_confirmed(session, app, client):
    endpoint = endpoints.RegisterEndpoint(
        User, secret="s0secret", form_template="<html>${error}</html>"
    )

    @app.post("/register")
    async def _post(
        username: str = fastapi.Form(None),
        password: str = fastapi.Form(None),
        confirm_password: str = fastapi.Form(None),
        email: str = fastapi.Form(None),
    ):
        return await endpoint.on_post(
            BASE_URL,
            session,
            username=username,
            email=email,
            password=password,
            confirm_password=confirm_password,
        )

    res = client.post(
        "/register",
        data={
            "username": "testuser",
            "password": "passw0rd",
            "confirm_password": "other",
            "email": "recipient@test.com",
        },
    )
    assert res.status_code == 400
    assert res.text == "<html>The specified passwords do not match.</html>"


def test_register_post_password_too_small(session, app, client, mocker):
    endpoint = endpoints.RegisterEndpoint(
        User,
        secret="s0secret",
        sender=SENDER,
        form_template="<html>${error}</html>",
    )
    mocker.patch.object(endpoint, "send_email_confirmation")

    @app.post("/register")
    async def _post(
        username: str = fastapi.Form(None),
        password: str = fastapi.Form(None),
        confirm_password: str = fastapi.Form(None),
        email: str = fastapi.Form(None),
    ):
        return await endpoint.on_post(
            BASE_URL,
            session,
            username=username,
            email=email,
            password=password,
            confirm_password=confirm_password,
        )

    res = client.post(
        "/register",
        data={
            "username": "testuser",
            "password": "6" * 6,
            "email": "recipient@test.com",
        },
    )
    assert res.status_code == 400
    msg = "Invalid password - the password must be at least 7 characters."
    assert res.text == f"<html>{msg}</html>"


def test_register_post_redo_unconfirmed(session, app, client, mocker):
    user = User(username="testuser", email="recipient@test.com")
    session.add(user)
    session.commit()

    endpoint = endpoints.RegisterEndpoint(
        User,
        secret="s0secret",
        sender=SENDER,
        sent_template="<html>${username} <${email}></html>",
    )
    mocker.patch.object(endpoint, "send_email_confirmation")

    @app.post("/register")
    async def _post(
        username: str = fastapi.Form(None),
        password: str = fastapi.Form(None),
        confirm_password: str = fastapi.Form(None),
        email: str = fastapi.Form(None),
    ):
        return await endpoint.on_post(
            BASE_URL,
            session,
            username=username,
            email=email,
            password=password,
            confirm_password=confirm_password,
        )

    res = client.post(
        "/register",
        data={
            "username": "testuser",
            "password": "passw0rd",
            "email": "recipient@test.com",
        },
    )
    assert res.status_code == 200
    assert res.text == "<html>testuser <recipient@test.com></html>"

    assert user.verify("passw0rd")


def test_register_post_user_already_confirmed(session, app, client, mocker):
    user = User(
        username="testuser",
        email="recipient@test.com",
        confirmed_at=datetime.now(),
    )
    session.add(user)
    session.commit()

    endpoint = endpoints.RegisterEndpoint(
        User,
        secret="s0secret",
        sender=SENDER,
        sent_template="<html>${username} <${email}></html>",
    )
    mocker.patch.object(endpoint, "send_email_confirmation")

    @app.post("/register")
    async def _post(
        username: str = fastapi.Form(None),
        password: str = fastapi.Form(None),
        confirm_password: str = fastapi.Form(None),
        email: str = fastapi.Form(None),
    ):
        return await endpoint.on_post(
            BASE_URL,
            session,
            username=username,
            email=email,
            password=password,
            confirm_password=confirm_password,
        )

    res = client.post(
        "/register",
        data={
            "username": "testuser",
            "password": "passw0rd",
            "email": "recipient@test.com",
        },
    )
    assert res.status_code == 200
    assert res.text == "<html>testuser <recipient@test.com></html>"


def test_register_post_duplicate_email(session, app, client, mocker):
    user = User(username="testuser", email="recipient@test.com")
    session.add(user)
    session.commit()

    endpoint = endpoints.RegisterEndpoint(
        User,
        secret="s0secret",
        sender=SENDER,
        form_template="<html>${error}</html>",
    )
    mocker.patch.object(endpoint, "send_email_confirmation")

    @app.post("/register")
    async def _post(
        username: str = fastapi.Form(None),
        password: str = fastapi.Form(None),
        confirm_password: str = fastapi.Form(None),
        email: str = fastapi.Form(None),
    ):
        return await endpoint.on_post(
            BASE_URL,
            session,
            username=username,
            email=email,
            password=password,
            confirm_password=confirm_password,
        )

    res = client.post(
        "/register",
        data={
            "username": "testuser2",
            "password": "passw0rd",
            "email": "recipient@test.com",
        },
    )
    assert res.status_code == 409
    assert res.text == "<html>That email address already exists.</html>"


def test_register_post_duplicate_username(session, app, client, mocker):
    user = User(username="testuser", email="recipient@test.com")
    session.add(user)
    session.commit()

    endpoint = endpoints.RegisterEndpoint(
        User,
        secret="s0secret",
        sender=SENDER,
        form_template="<html>${error}</html>",
    )
    mocker.patch.object(endpoint, "send_email_confirmation")

    @app.post("/register")
    async def _post(
        username: str = fastapi.Form(None),
        password: str = fastapi.Form(None),
        confirm_password: str = fastapi.Form(None),
        email: str = fastapi.Form(None),
    ):
        return await endpoint.on_post(
            BASE_URL,
            session,
            username=username,
            email=email,
            password=password,
            confirm_password=confirm_password,
        )

    res = client.post(
        "/register",
        data={
            "username": "testuser",
            "password": "passw0rd",
            "email": "recipient2@test.com",
        },
    )
    assert res.status_code == 409
    assert res.text == "<html>That username already exists.</html>"


def test_send_email_confirmation(mocker):
    endpoint = endpoints.RegisterEndpoint(
        User,
        secret="s0secret",
        sender=SENDER,
        confirmation_text_template="<url: ${confirm_url}",
        confirmation_html_template="<html>url: ${confirm_url}</html>",
    )
    send_message = mocker.patch.object(endpoint, "send_message")

    base_url = "http://local.test.com/"
    email = "recipient2@test.com"
    confirmation_token = URLSafeTimedSerializer(endpoint.secret).dumps(
        email, salt=endpoint.salt
    )
    confirmation_url = f"{base_url}{endpoint.confirm_url}{confirmation_token}"

    endpoint.send_email_confirmation(base_url=base_url, email=email)
    msg = send_message.call_args[0][0]
    assert msg["Subject"] == endpoint.email_subject
    assert msg["From"] == endpoint.sender
    assert msg["To"] == email

    parts = msg.get_payload()
    assert len(parts) == 2
    assert parts[0].get_content_type() == "text/plain"
    assert (
        parts[0].get_payload().replace("=\n", "")
        == f"<url: {confirmation_url}\n"
    )
    assert parts[1].get_content_type() == "text/html"
    assert (
        parts[1].get_payload().replace("=\n", "")
        == f"<html>url: {confirmation_url}</html>\n"
    )


def test_send_email_confirmation_fail(mocker):
    endpoint = endpoints.RegisterEndpoint(
        User,
        secret="s0secret",
        sender=SENDER,
    )

    send_message = mocker.patch.object(
        endpoint, "send_message", side_effect=Exception
    )

    endpoint.send_email_confirmation(
        base_url="http://local.test.com/", email="recipient2@test.com"
    )
    assert send_message.called


def test_send_message_ssl(mocker):
    endpoint = endpoints.RegisterEndpoint(
        User,
        secret="s0secret",
        sender=SENDER,
        email_use_ssl=True,
        email_use_tls=True,
        email_login="user1",
        email_password="passwd1",
    )

    mock_smtp = mocker.Mock()
    create_default_context = mocker.patch("ssl.create_default_context")
    smtp_ssl = mocker.patch("smtplib.SMTP_SSL", return_value=mock_smtp)

    msg = mocker.Mock()
    endpoint.send_message(msg)

    assert smtp_ssl.call_args == mocker.call(
        endpoint.email_server, endpoint.email_port
    )
    assert mock_smtp.mock_calls == [
        mocker.call.starttls(context=create_default_context.return_value),
        mocker.call.login(endpoint.email_login, endpoint.email_password),
        mocker.call.send_message(msg),
        mocker.call.close(),
    ]


def test_send_message_no_ssl(mocker):
    endpoint = endpoints.RegisterEndpoint(
        User,
        secret="s0secret",
        sender=SENDER,
        email_use_ssl=False,
        email_use_tls=True,
        email_login="user1",
        email_password="passwd1",
    )

    mock_smtp = mocker.Mock()
    create_default_context = mocker.patch("ssl.create_default_context")
    smtp = mocker.patch("smtplib.SMTP", return_value=mock_smtp)

    msg = mocker.Mock()
    endpoint.send_message(msg)

    assert smtp.call_args == mocker.call(
        endpoint.email_server, endpoint.email_port
    )
    assert mock_smtp.mock_calls == [
        mocker.call.starttls(context=create_default_context.return_value),
        mocker.call.login(endpoint.email_login, endpoint.email_password),
        mocker.call.send_message(msg),
        mocker.call.close(),
    ]


def test_register_post_no_confirmation_email(session, app, client):
    endpoint = endpoints.RegisterEndpoint(
        User, secret="s0secret", form_template="<html>${error}</html>"
    )

    @app.post("/register")
    async def _post(
        username: str = fastapi.Form(None),
        password: str = fastapi.Form(None),
        confirm_password: str = fastapi.Form(None),
        email: str = fastapi.Form(None),
    ):
        return await endpoint.on_post(
            BASE_URL,
            session,
            username=username,
            email=email,
            password=password,
            confirm_password=confirm_password,
        )

    res = client.post(
        "/register",
        data={
            "username": "testuser",
            "password": "passw0rd",
            "email": "recipient@test.com",
        },
    )
    assert res.status_code == 303
    assert res.headers.get("location") == "/"
