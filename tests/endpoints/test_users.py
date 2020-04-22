import uuid

import pytest
from fastapi import HTTPException

from apitoolbox.endpoints import UsersEndpoint
from tests.data import models


def test_users_endpoint(session, loop):
    user = models.User(username="user-1")
    session.add(user)

    permissions = [models.Permission(name=name) for name in ["read", "write"]]
    session.add_all(permissions)
    session.commit()

    permission_ids = [model.id for model in permissions]

    endpoint = UsersEndpoint(models.User)

    # Set User Permissions
    user_permissions_list = loop.run_until_complete(
        endpoint.set_user_permissions(
            session, user.id, permission_ids, models.Permission
        )
    )
    assert user_permissions_list == sorted([
        {
            "id": str(permissions[0].id),
            "name": permissions[0].name,
            "created_at": permissions[0].created_at.isoformat(),
            "updated_at": permissions[0].updated_at.isoformat(),
        },
        {
            "id": str(permissions[1].id),
            "name": permissions[1].name,
            "created_at": permissions[1].created_at.isoformat(),
            "updated_at": permissions[1].updated_at.isoformat(),
        }
    ], key=lambda obj: obj["id"])

    # List User Permissions
    user_permissions = loop.run_until_complete(
        endpoint.list_user_permissions(session, user.id)
    )
    assert user_permissions_list == user_permissions


def test_users_endpoint_invalid_id(session, loop):
    user = models.User(username="user-1")
    session.add(user)
    session.commit()

    endpoint = UsersEndpoint(models.User)

    nonexistent_uuids = [uuid.uuid4()]

    # Test
    with pytest.raises(HTTPException) as exc_info:
        loop.run_until_complete(
            endpoint.set_user_permissions(
                session, user.id, nonexistent_uuids, models.Permission
            )
        )
    assert exc_info.value.status_code == 422
    msg = f"Invalid permission IDs: {nonexistent_uuids}"
    assert exc_info.value.detail == msg
