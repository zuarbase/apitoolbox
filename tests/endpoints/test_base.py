from pydantic import BaseModel

from apitoolbox.endpoints.base import BaseCrudEndpoint
from tests.data import models


class UserBaseModel(BaseModel):
    username: str


class UserCreateModel(UserBaseModel):
    password: str


def test_base_model_flow(session, loop):
    """Test `BaseCrudEndpoint` using user model."""
    endpoint = BaseCrudEndpoint(models.User)

    # Create
    data = {
        "username": "user-1",
        "password": "my_password"
    }
    user_dict = loop.run_until_complete(
        endpoint.create(session, UserCreateModel(**data))
    )
    user = session.query(models.User).filter(
        models.User.id == user_dict["id"]
    ).one()
    user_id = user.id
    data.pop("password")
    assert user_dict == {
        **data,
        "id": str(user.id),
        "created_at": user.created_at.isoformat(),
        "updated_at": user.updated_at.isoformat()
    }

    # List all
    results = loop.run_until_complete(
        endpoint.list(session)
    )
    assert results == [user_dict]

    # Get by ID
    result = loop.run_until_complete(
        endpoint.retrieve(session, user_id)
    )
    assert result == user_dict

    # Update
    data = {
        "username": "user-1-updated"
    }
    user_dict_updated = loop.run_until_complete(
        endpoint.update(session, user_id, UserBaseModel(**data))
    )
    assert user_dict_updated == {
        **user_dict,
        **data,
        "updated_at": user.updated_at.isoformat()
    }

    # Delete
    loop.run_until_complete(
        endpoint.delete(session, user_id)
    )
    user = session.query(models.User).filter(
        models.User.id == user_dict["id"]
    ).first()
    assert user is None
