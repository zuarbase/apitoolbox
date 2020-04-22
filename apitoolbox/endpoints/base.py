"""Common implementation of CRUD endpoints."""
from typing import Any, Dict, List

from pydantic import BaseModel
from sqlalchemy.orm import Session

from apitoolbox import crud


class BaseCrudEndpoint:
    """Class-based endpoint for common CRUD endpoints."""

    def __init__(self, entity_cls):
        self.entity_cls = entity_cls

    async def list(self, session: Session) -> List[Dict[str, Any]]:
        """Get all instances."""
        return await crud.list_instances(self.entity_cls, session)

    async def retrieve(self, session: Session, instance_id) -> Dict[str, Any]:
        """Get an instance by ID."""
        return await crud.retrieve_instance(
            self.entity_cls, session, instance_id
        )

    async def create(self, session: Session, data: BaseModel) -> Dict[str, Any]:
        """Create an instance."""
        return await crud.create_instance(
            self.entity_cls, session, data
        )

    async def update(
            self,
            session: Session,
            instance_id,
            data: BaseModel
    ) -> Dict[str, Any]:
        """Update an instance by ID."""
        return await crud.update_instance(
            self.entity_cls, session, instance_id, data
        )

    async def delete(
            self,
            session: Session,
            instance_id
    ):
        """Delete an instance by ID."""
        await crud.delete_instance(
            self.entity_cls, session, instance_id
        )
