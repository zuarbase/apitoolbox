"""CRUD endpoints for users."""
from typing import Any, Dict, List, Type
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from apitoolbox import models
from apitoolbox.endpoints.base import BaseCrudEndpoint


class UsersEndpoint(BaseCrudEndpoint):
    """Class-based endpoint for users."""

    async def list_user_permissions(
            self,
            session: Session,
            user_id
    ) -> List[Dict[str, Any]]:
        """List all user permissions."""
        await self.retrieve(session, user_id)

        user = session.query(self.entity_cls).get(user_id)
        return [entity.as_dict() for entity in user.user_permissions]

    async def set_user_permissions(
            self,
            session: Session,
            user_id,
            permission_ids: List[UUID],
            permission_cls: Type[models.Permission]
    ) -> List[Dict[str, Any]]:
        """Set user permissions."""
        await self.retrieve(session, user_id)

        user = session.query(self.entity_cls).get(user_id)
        permissions = session.query(permission_cls).\
            filter(permission_cls.id.in_(permission_ids)).\
            order_by(permission_cls.id).\
            all()
        if len(permissions) != len(permission_ids):
            found_ids = {model.id for model in permissions}
            not_found_ids = list(found_ids.symmetric_difference(permission_ids))
            raise HTTPException(
                422, f"Invalid permission IDs: {not_found_ids}")

        user.user_permissions = permissions
        session.commit()
        return [entity.as_dict() for entity in permissions]
