""" Utility functions """
import uuid
import time

from string import Template
from typing import Union

import sqlalchemy
from sqlalchemy import exc
from sqlalchemy.engine import Connection, ResultProxy

import jwt
from starlette.requests import Request

try:
    from ordered_uuid import OrderedUUID
except ImportError:
    OrderedUUID = None


def ordered_uuid(value=None) -> OrderedUUID:
    """ Generate a rearranged uuid1 that is ordered by time.
    This is a more efficient for use as a primary key, see:
    https://www.percona.com/blog/2014/12/19/store-uuid-optimized-way/
    """
    if OrderedUUID is None:
        raise RuntimeError("ordered_uuid package: not found")
    if not value:
        value = str(uuid.uuid1())
    return OrderedUUID(value)


def render(
        path_or_template: Union[str, Template],
        **kwargs,
) -> str:
    """ Render the specified template - either a file or the actual template """
    if isinstance(path_or_template, Template):
        template = path_or_template
    elif path_or_template.startswith("<"):
        template = Template(path_or_template)
    else:
        with open(path_or_template, "r") as filp:
            contents = filp.read()
        template = Template(contents)
    return template.safe_substitute(**kwargs)


def get_session(request: Request):
    """Get `request.state.session`

    Usage:
        >>> from fastapi import Depends
        >>> session = Depends(get_session)
    """
    return request.state.session


def jwt_encode(payload: dict, secret: str, algorithm: str = "HS256") -> str:
    """ Encode the given payload as a JWT """
    assert "exp" in payload
    return jwt.encode(
        payload,
        str(secret),
        algorithm=algorithm,
    ).decode("utf-8")


def db_execute(
        execute_obj,
        *query_args,
        max_query_retry_attempts: int = 2,
        query_retry_timeout: float = 2, **query_kwargs
) -> ResultProxy:
    """
    Execute the given query and make a retry logic if a DB connection was lost
    and connection was invalidated.
    This method is an alternative to the `pool_pre_ping` engine  feature but it
    does not execute an additional `SELECT 1` overhead DB request.
    ----
    We need to force call connect() to recreate new connection with Connection
      type only since:
      - Engine execute() creates new connection each time on execute
      - Cursor/Session/Query will get a new connection from the pool after the
       current one was invalidated (e.g. after disconnect exception was raised)
    """
    n_attempts = 0
    last_err = None
    while n_attempts <= max_query_retry_attempts:
        n_attempts += 1
        try:
            return execute_obj.execute(*query_args, **query_kwargs)
        except exc.DBAPIError as err:
            if not err.connection_invalidated:
                raise err

            if isinstance(execute_obj, Connection):
                execute_obj = execute_obj.connect()

            time.sleep(query_retry_timeout)
            last_err = err
    raise last_err


def create_engine(
        dbo: str,
        **kwargs
) -> sqlalchemy.engine.Engine:
    """ Instantiate an engine """
    if dbo.startswith("snowflake"):
        kwargs.setdefault(
            "pool_pre_ping", False)  # Skip connection ping (e.g. "SELECT 1")
        kwargs.setdefault(
            "pool_reset_on_return", None)  # Do nothing on connection "check-in"
        kwargs.setdefault(
            "_initialize", False)  # Skip "first_connect" initialization
    else:
        kwargs.setdefault("pool_pre_ping", True)

    engine = sqlalchemy.create_engine(dbo, **kwargs)

    if dbo.startswith("snowflake:"):
        db_execute(
            engine,
            "alter session set quoted_identifiers_ignore_case = true;"
        )

    return engine
