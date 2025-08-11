""" Generic CRUD operations """
from typing import Any, Dict, List, Union
from uuid import UUID

import sqlalchemy.exc
from pydantic import BaseModel, PositiveInt
from sqlalchemy_filters import apply_filters, apply_sort
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException

from . import models, types

# NOTE: always use the session of the caller
# i.e. don't us models.Session in the thread pool synchronous functions
# This is necessary in sqlite3 (at least) to ensure consistency.


async def list_instances(
    cls: models.BASE,
    session: models.Session,
    filter_spec: List[Dict[str, Any]] = None,
    sort_spec: List[Dict[str, str]] = None,
    offset: types.NonNegativeInt = 0,
    limit: PositiveInt = None,
    options: Any = None,
) -> List[dict]:
    """Return all instances of cls"""
    # pylint: disable=too-many-arguments
    query = session.query(cls)
    if filter_spec:
        query = apply_filters(query, filter_spec)
    if sort_spec:
        query = apply_sort(query, sort_spec)

    if options:
        query = query.options(options)

    if limit:
        query = query.limit(limit)
    query = query.offset(offset)

    def _list():
        return [instance.as_dict() for instance in query.all()]

    return await run_in_threadpool(_list)


async def count_instances(
    cls: models.BASE,
    session: models.Session,
    filter_spec: List[Dict[str, Any]] = None,
    sort_spec: List[Dict[str, Any]] = None,
) -> int:
    """Total count of instances matching the given criteria"""
    query = session.query(cls)
    if filter_spec:
        query = apply_filters(query, filter_spec)
    if sort_spec:
        query = apply_sort(query, sort_spec)

    def _count():
        return query.count()

    return await run_in_threadpool(_count)


async def create_instance(
    cls: models.BASE, session: models.Session, data: Union[BaseModel, dict],
    commit: bool = True,
) -> dict:
    """Create an instances of cls with the provided data"""
    if isinstance(data, BaseModel):
        create_data = data.dict()
    else:
        create_data = data
    instance = cls(**create_data)

    def _create():
        session.add(instance)
        if commit:
            session.commit()
        return session.merge(instance).as_dict()

    try:
        return await run_in_threadpool(_create)
    except sqlalchemy.exc.IntegrityError as exc:
        raise HTTPException(status_code=409, detail=str(exc.orig)) from exc


async def retrieve_instance(
    cls: models.BASE,
    session: models.Session,
    instance_id: UUID,
    options: Any = None,
) -> dict:
    """Get an instance of cls by UUID"""
    query = session.query(cls)

    if options:
        query = query.options(options)

    def _retrieve():
        instance = query.get(instance_id)
        if instance:
            return instance.as_dict()
        return None

    data = await run_in_threadpool(_retrieve)
    if data is None:
        raise HTTPException(status_code=404)
    return data


async def update_instance(
    cls: models.BASE,
    session: models.Session,
    instance_id: UUID,
    data: Union[BaseModel, dict],
    commit: bool = True,
) -> dict:
    """Partial update an instance using the provided data"""

    if isinstance(data, BaseModel):
        update_data = data.dict(exclude_unset=True)
    else:
        update_data = data

    def _update():
        instance = session.query(cls).get(instance_id)
        if not instance:
            return None
        for key, value in update_data.items():
            setattr(instance, key, value)
        if commit:
            session.commit()
        return session.merge(instance).as_dict()

    data = await run_in_threadpool(_update)
    if data is None:
        raise HTTPException(status_code=404)
    return data


async def delete_instance(
    cls: models.BASE, session: models.Session, instance_id: UUID,
    commit: bool = True,
) -> dict:
    """Delete an instance by UUID"""

    def _delete():
        instance = session.query(cls).get(instance_id)
        if not instance:
            return None
        result = instance.as_dict()
        session.delete(instance)
        if commit:
            session.commit()
        return result

    data = await run_in_threadpool(_delete)
    if data is None:
        raise HTTPException(status_code=404)
    return data
