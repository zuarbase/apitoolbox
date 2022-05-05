import pytest
from fastapi import Depends
from starlette.authentication import SimpleUser
from starlette.datastructures import State
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.requests import Request

from apitoolbox import auth, middleware, models


class User(models.User, models.mixins.DictMixin):
    __tablename__ = "test_middleware_users"
    __model_mapping__ = False


def test_auth(session, app, client):
    user = User(username="testuser")
    session.add(user)
    session.commit()

    admin_scope = "admin"

    @app.get("/ping")
    def _ping():
        return "pong"

    @app.get(
        "/me",
        dependencies=[
            Depends(auth.validate_authenticated),
        ],
    )
    def _get(request: Request):
        return {
            "username": request.user.username,
            "scopes": request.auth.scopes,
        }

    @app.get(
        "/scopes/all",
        dependencies=[
            Depends(
                auth.AllScopesValidator(
                    scopes=["read", "write", "me"], admin_scope=admin_scope
                )
            )
        ],
    )
    def _scopes_all(request: Request):
        return {
            "username": request.user.username,
            "scopes": request.auth.scopes,
        }

    @app.get(
        "/scopes/any",
        dependencies=[
            Depends(
                auth.AnyScopeValidator(
                    scopes=["read", "write"], admin_scope=admin_scope
                )
            )
        ],
    )
    def _scopes_any(request: Request):
        return {
            "username": request.user.username,
            "scopes": request.auth.scopes,
        }

    @app.get(
        "/admin",
        dependencies=[Depends(auth.AdminValidator(admin_scope=admin_scope))],
    )
    def _admin(request: Request):
        return {
            "username": request.user.username,
            "scopes": request.auth.scopes,
        }

    app.add_middleware(
        AuthenticationMiddleware,
        backend=auth.PayloadAuthBackend(
            user_cls=User, admin_scope=admin_scope
        ),
    )
    app.add_middleware(middleware.UpstreamPayloadMiddleware)
    app.add_middleware(middleware.SessionMiddleware, bind=session.bind)

    payload_prefix = middleware.UpstreamPayloadMiddleware.PAYLOAD_HEADER_PREFIX

    # Test /ping - no auth & authz required
    res = client.get("/ping")
    assert res.status_code == 200, res.text
    assert res.text == '"pong"'

    # Test /me - not authenticated
    res = client.get(
        "/me", headers={f"{payload_prefix}username": "nonexistent_user"}
    )
    assert res.status_code == 401

    # Test /me - success
    res = client.get(
        "/me", headers={f"{payload_prefix}username": user.username}
    )
    assert res.status_code == 200, res.text
    assert res.json() == {"username": user.username, "scopes": []}

    # Test /scopes/all - not authenticated
    res = client.get(
        "/scopes/all",
        headers={
            f"{payload_prefix}username": "nonexistent_user",
            f"{payload_prefix}permissions": "read,write",
        },
    )
    assert res.status_code == 401

    # Test /scopes/all - missing required scope
    res = client.get(
        "/scopes/all",
        headers={
            f"{payload_prefix}username": user.username,
            f"{payload_prefix}permissions": "read,write",  # no "me" scope
        },
    )
    assert res.status_code == 403

    # Test /scopes/all - success
    res = client.get(
        "/scopes/all",
        headers={
            f"{payload_prefix}username": user.username,
            f"{payload_prefix}permissions": "read,write,me",
        },
    )
    assert res.status_code == 200, res.text
    assert res.json() == {
        "username": user.username,
        "scopes": ["read", "write", "me"],
    }

    # Test /scopes/all - admin scope - success
    res = client.get(
        "/scopes/all",
        headers={
            f"{payload_prefix}username": user.username,
            # not specified in endpoint
            f"{payload_prefix}permissions": admin_scope,
        },
    )
    assert res.status_code == 200, res.text
    assert res.json() == {"username": user.username, "scopes": [admin_scope]}

    # Test /scopes/any - not authenticated
    res = client.get(
        "/scopes/any",
        headers={f"{payload_prefix}username": "nonexistent_user"},
    )
    assert res.status_code == 401

    # Test /scopes/any - request without any scope
    res = client.get(
        "/scopes/any", headers={f"{payload_prefix}username": user.username}
    )
    assert res.status_code == 403

    # Test /scopes/any - request with only "read" scope
    res = client.get(
        "/scopes/any",
        headers={
            f"{payload_prefix}username": user.username,
            f"{payload_prefix}permissions": "read",
        },
    )
    assert res.status_code == 200
    assert res.json() == {"username": user.username, "scopes": ["read"]}

    # Test /scopes/any - admin scope - success
    res = client.get(
        "/scopes/any",
        headers={
            f"{payload_prefix}username": user.username,
            f"{payload_prefix}permissions": admin_scope,
        },
    )
    assert res.status_code == 200
    assert res.json() == {"username": user.username, "scopes": [admin_scope]}

    # Test /admin - failed - no admin scope
    res = client.get(
        "/admin",
        headers={
            "X-Payload-username": user.username,
            "X-Payload-permissions": "non-admin-scope",
        },
    )
    assert res.status_code == 403

    # Test /admin - admin scope required
    res = client.get(
        "/admin",
        headers={
            "X-Payload-username": user.username,
            "X-Payload-permissions": f"{admin_scope},read",
        },
    )
    assert res.status_code == 200, res.text
    assert res.json() == {"username": user.username, "scopes": [admin_scope]}


def test_payload_auth_backend():
    backend = auth.PayloadAuthBackend(user_cls=User, admin_scope="admin")
    assert backend.user_cls is User
    assert backend.admin_scope == "admin"


def test_payload_auth_backend_no_user_cls(mocker, loop):
    expected_username = "user1"

    backend = auth.PayloadAuthBackend()

    mock_conn = mocker.Mock(
        state=State({"payload": {"username": expected_username}})
    )
    result = loop.run_until_complete(backend.authenticate(mock_conn))
    assert result is not None
    assert len(result) == 2
    assert isinstance(result[1], SimpleUser)
    assert result[1].username == expected_username


def test_payload_auth_backend_scopes(loop):
    backend = auth.PayloadAuthBackend(admin_scope="admin")

    result = loop.run_until_complete(backend.scopes({"scopes": "read, write"}))
    assert result == ["read", "write"]

    result = loop.run_until_complete(
        backend.scopes({"permissions": "read, write"})
    )
    assert result == ["read", "write"]

    result = loop.run_until_complete(backend.scopes({}))
    assert result == []

    result = loop.run_until_complete(backend.scopes({"permissions": "admin"}))
    assert result == ["admin"]


def test_payload_auth_backend_missing_payload_error(mocker, loop):
    backend = auth.PayloadAuthBackend()

    mock_conn = mocker.Mock(state=State())
    with pytest.raises(RuntimeError) as exc_info:
        loop.run_until_complete(backend.authenticate(mock_conn))

    error_msg = (
        "Missing 'request.state.payload': "
        "try adding 'middleware.UpstreamPayloadMiddleware'"
    )
    assert str(exc_info.value) == error_msg


def test_payload_auth_backend_missing_session_error(mocker, loop):
    backend = auth.PayloadAuthBackend(user_cls=User)

    mock_conn = mocker.Mock(state=State({"payload": {"username": "user1"}}))
    with pytest.raises(RuntimeError) as exc_info:
        loop.run_until_complete(backend.authenticate(mock_conn))

    error_msg = (
        "Missing 'request.state.session': "
        "try adding 'middleware.SessionMiddleware'"
    )
    assert str(exc_info.value) == error_msg
