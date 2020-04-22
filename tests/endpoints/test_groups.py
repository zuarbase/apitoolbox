import uuid

import pytest
from fastapi import HTTPException

from apitoolbox.endpoints import GroupsEndpoint
from tests.data import models


def test_groups_endpoint(session, loop):
    users = [models.User(username=name) for name in ["user-1", "user-2"]]
    session.add_all(users)

    group = models.Group(name="admins")
    session.add(group)

    permissions = [models.Permission(name=name) for name in ["read", "write"]]
    session.add_all(permissions)
    session.commit()

    user_ids = [model.id for model in users]
    permission_ids = [model.id for model in permissions]

    endpoint = GroupsEndpoint(models.Group)

    # Set Group Permissions
    group_permissions_list = loop.run_until_complete(
        endpoint.set_group_permissions(
            session, group.id, permission_ids, models.Permission
        )
    )
    assert group_permissions_list == sorted([
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

    # List Group Permissions
    group_permissions = loop.run_until_complete(
        endpoint.list_group_permissions(session, group.id)
    )
    assert group_permissions_list == group_permissions

    # Set Group members
    group_users_list = loop.run_until_complete(
        endpoint.set_group_members(
            session, group.id, user_ids, models.User
        )
    )
    assert group_users_list == sorted([
        {
            "id": str(users[0].id),
            "username": users[0].username,
            "created_at": users[0].created_at.isoformat(),
            "updated_at": users[0].updated_at.isoformat(),
        },
        {
            "id": str(users[1].id),
            "username": users[1].username,
            "created_at": users[1].created_at.isoformat(),
            "updated_at": users[1].updated_at.isoformat(),
        }
    ], key=lambda obj: obj["id"])

    # List Group members
    group_users = loop.run_until_complete(
        endpoint.list_group_members(session, group.id)
    )
    assert group_users_list == group_users


def test_groups_endpoint_invalid_id(session, loop):
    group = models.Group(name="admins")
    session.add(group)
    session.commit()

    endpoint = GroupsEndpoint(models.Group)

    nonexistent_uuids = [uuid.uuid4()]

    # Test
    with pytest.raises(HTTPException) as exc_info:
        loop.run_until_complete(
            endpoint.set_group_permissions(
                session, group.id, nonexistent_uuids, models.Permission
            )
        )
    assert exc_info.value.status_code == 422
    msg = f"Invalid permission IDs: {nonexistent_uuids}"
    assert exc_info.value.detail == msg

    with pytest.raises(HTTPException) as exc_info:
        loop.run_until_complete(
            endpoint.set_group_members(
                session, group.id, nonexistent_uuids, models.User
            )
        )
    assert exc_info.value.status_code == 422
    msg = f"Invalid user IDs: {nonexistent_uuids}"
    assert exc_info.value.detail == msg
