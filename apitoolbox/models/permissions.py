""" Permission model """
import sqlalchemy
from sqlalchemy import event

from . import mixins
from .base import BASE, MODEL_MAPPING, Session


class Permission(BASE, mixins.GuidMixin, mixins.TimestampMixin):
    """The permissions table"""

    __tablename__ = "permissions"
    __abstract__ = True

    name = sqlalchemy.Column(
        sqlalchemy.String(255),
        nullable=False,
        unique=True,
    )

    @classmethod
    def get_by_name(cls, session: Session, name: str):
        """Lookup a group by name"""
        return session.query(cls).filter(cls.name == name).first()


@event.listens_for(Permission, "mapper_configured", propagate=True)
def _mapper_configured(_mapper, cls):
    MODEL_MAPPING["Permission"] = cls
