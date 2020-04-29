import pytest
from fastapi import Depends, Security
from starlette.authentication import SimpleUser
from starlette.datastructures import State

from apitoolbox import auth, middleware, models


class User(
        models.User, models.mixins.DictMixin
):
    __tablename__ = "test_middleware_users"
    __model_mapping__ = False


def test_auth(session, app, client):
    user = User(username="testuser")
    session.add(user)
    session.commit()

    admin_scope = "admin"
    payload_auth = auth.PayloadAuth(user_cls=User, admin_scope=admin_scope)

    @app.get("/ping")
    def _ping():
        return "pong"

    @app.get("/me")
    def _get(user_: User = Depends(payload_auth)):
        return {"username": user_.username}

    @app.get("/scopes/all")
    def _scopes_all(
            user_: User = Security(
                payload_auth.all_scopes,
                scopes=["read", "write", "me"]
            )
    ):
        return {"username": user_.username}

    @app.get("/scopes/any")
    def _scopes_any(
            user_: User = Security(
                payload_auth.any_scope,
                scopes=["read", "write"]
            )
    ):
        return {"username": user_.username}

    @app.get("/admin")
    def _admin(
            user_: User = Depends(payload_auth.admin)
    ):
        return {"username": user_.username}

    app.add_middleware(middleware.UpstreamPayloadMiddleware)
    app.add_middleware(middleware.SessionMiddleware, bind=session.bind)

    payload_prefix = middleware.UpstreamPayloadMiddleware.PAYLOAD_HEADER_PREFIX

    # Test /ping - no auth & authz required
    res = client.get("/ping")
    assert res.status_code == 200, res.text
    assert res.text == '"pong"'

    # Test /me - no payload
    res = client.get("/me", headers={})
    assert res.status_code == 401

    # Test /me - not authenticated
    res = client.get("/me", headers={
        f"{payload_prefix}username": "nonexistent_user"
    })
    assert res.status_code == 401

    # Test /me - success
    res = client.get("/me", headers={
        f"{payload_prefix}username": user.username
    })
    assert res.status_code == 200, res.text
    assert res.json() == {
        "username": user.username
    }

    # Test /scopes/all - not authenticated
    res = client.get("/scopes/all", headers={
        f"{payload_prefix}username": "nonexistent_user",
        f"{payload_prefix}permissions": "read,write"
    })
    assert res.status_code == 401

    # Test /scopes/all - missing required scope
    res = client.get("/scopes/all", headers={
        f"{payload_prefix}username": user.username,
        f"{payload_prefix}permissions": "read,write"  # no "me" scope
    })
    assert res.status_code == 403

    # Test /scopes/all - success
    res = client.get("/scopes/all", headers={
        f"{payload_prefix}username": user.username,
        f"{payload_prefix}permissions": "read,write,me"
    })
    assert res.status_code == 200, res.text
    assert res.json() == {
        "username": user.username
    }

    # Test /scopes/all - admin scope - success
    res = client.get("/scopes/all", headers={
        f"{payload_prefix}username": user.username,
        f"{payload_prefix}permissions": admin_scope  # not specified in endpoint
    })
    assert res.status_code == 200, res.text
    assert res.json() == {
        "username": user.username
    }

    # Test /scopes/any - not authenticated
    res = client.get("/scopes/any", headers={
        f"{payload_prefix}username": "nonexistent_user"
    })
    assert res.status_code == 401

    # Test /scopes/any - request without any scope
    res = client.get("/scopes/any", headers={
        f"{payload_prefix}username": user.username
    })
    assert res.status_code == 403

    # Test /scopes/any - request with only "read" scope
    res = client.get("/scopes/any", headers={
        f"{payload_prefix}username": user.username,
        f"{payload_prefix}permissions": "read"
    })
    assert res.status_code == 200
    assert res.json() == {
        "username": user.username
    }

    # Test /scopes/any - admin scope - success
    res = client.get("/scopes/any", headers={
        f"{payload_prefix}username": user.username,
        f"{payload_prefix}permissions": admin_scope  # not specified in endpoint
    })
    assert res.status_code == 200
    assert res.json() == {
        "username": user.username
    }

    # Test /admin - failed - no admin scope
    res = client.get("/admin", headers={
        "X-Payload-username": user.username,
        "X-Payload-permissions": "non-admin-scope"
    })
    assert res.status_code == 403

    # Test /admin - admin scope required
    res = client.get("/admin", headers={
        "X-Payload-username": user.username,
        "X-Payload-permissions": f"{admin_scope},read"
    })
    assert res.status_code == 200, res.text
    assert res.json() == {
        "username": user.username
    }


def test_payload_auth_no_user_cls(mocker, loop):
    expected_username = "user1"

    backend = auth.PayloadAuth()

    mock_conn = mocker.Mock(state=State({
        "payload": {"username": expected_username}
    }))
    result = loop.run_until_complete(backend(mock_conn))
    assert isinstance(result, SimpleUser)
    assert result.username == expected_username
    assert result.is_authenticated is True


def test_payload_auth_scopes(loop):
    backend = auth.PayloadAuth(admin_scope="admin")

    result = backend.get_scopes({
        "scopes": "read, write"
    })
    assert result == ["read", "write"]

    result = backend.get_scopes({
        "permissions": "read, write"
    })
    assert result == ["read", "write"]

    result = backend.get_scopes({})
    assert result == []

    result = backend.get_scopes({
        "permissions": "admin"
    })
    assert result == ["admin"]


def test_payload_auth_backend_missing_payload_error(mocker, loop):
    backend = auth.PayloadAuth()

    mock_conn = mocker.Mock(state=State())
    with pytest.raises(RuntimeError) as exc_info:
        loop.run_until_complete(backend(mock_conn))

    error_msg = "Missing 'request.state.payload': " \
                "try adding 'middleware.UpstreamPayloadMiddleware'"
    assert str(exc_info.value) == error_msg


def test_payload_auth_missing_session_error(mocker, loop):
    backend = auth.PayloadAuth(user_cls=User)

    mock_conn = mocker.Mock(state=State({
        "payload": {"username": "user1"}
    }))
    with pytest.raises(RuntimeError) as exc_info:
        loop.run_until_complete(backend(mock_conn))

    error_msg = "Missing 'request.state.session': " \
                "try adding 'middleware.SessionMiddleware'"
    assert str(exc_info.value) == error_msg
