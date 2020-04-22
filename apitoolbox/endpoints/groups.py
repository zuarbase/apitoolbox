"""CRUD endpoints for groups."""
from typing import Any, Dict, List, Type
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from apitoolbox import models
from apitoolbox.endpoints.base import BaseCrudEndpoint


class GroupsEndpoint(BaseCrudEndpoint):
    """Class-based endpoint for groups."""

    async def list_group_permissions(
            self,
            session: Session,
            user_id: UUID
    ) -> List[Dict[str, Any]]:
        """List all group permissions."""
        await self.retrieve(session, user_id)

        group = session.query(self.entity_cls).get(user_id)
        return [entity.as_dict() for entity in group.permissions]

    async def set_group_permissions(
            self,
            session: Session,
            group_id: UUID,
            permission_ids: List[UUID],
            permission_cls: Type[models.Permission]
    ) -> List[Dict[str, Any]]:
        """Set group permissions."""
        await self.retrieve(session, group_id)

        group = session.query(self.entity_cls).get(group_id)
        permissions = session.query(permission_cls).\
            filter(permission_cls.id.in_(permission_ids)).\
            order_by(permission_cls.id).\
            all()
        if len(permissions) != len(permission_ids):
            found_ids = {model.id for model in permissions}
            not_found_ids = list(found_ids.symmetric_difference(permission_ids))
            raise HTTPException(
                422, f"Invalid permission IDs: {not_found_ids}")

        group.permissions = permissions
        session.commit()
        return [entity.as_dict() for entity in permissions]

    async def list_group_members(
            self,
            session: Session,
            user_id: UUID
    ) -> List[Dict[str, Any]]:
        """List all group members."""
        await self.retrieve(session, user_id)

        group = session.query(self.entity_cls).get(user_id)
        return [entity.as_dict() for entity in group.users]

    async def set_group_members(
            self,
            session: Session,
            group_id: UUID,
            user_ids: List[UUID],
            user_cls: Type[models.User]
    ) -> List[Dict[str, Any]]:
        """Set group members."""
        await self.retrieve(session, group_id)

        group = session.query(self.entity_cls).get(group_id)
        users = session.query(user_cls).\
            filter(user_cls.id.in_(user_ids)).\
            order_by(user_cls.id).\
            all()
        if len(users) != len(user_ids):
            found_ids = {model.id for model in users}
            not_found_ids = list(found_ids.symmetric_difference(user_ids))
            raise HTTPException(
                422, f"Invalid user IDs: {not_found_ids}")

        group.users = users
        session.commit()
        return [entity.as_dict() for entity in users]
