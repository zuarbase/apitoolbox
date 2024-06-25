"""
Database engines registry.

The registry is a single source of shared sqlalchemy engines.

NOTE: there are both thread-safe and non thread-safe functions.
"""
import threading
import typing

from sqlalchemy.engine import Connectable, Engine

from apitoolbox import utils

__LOCK = threading.Lock()

__ENGINE_REGISTRY: typing.Dict[str, Engine] = {}


def register(
    bind: typing.Union[str, Connectable], pool_pre_ping=True, **engine_kwargs
) -> Engine:
    """Register an engine or create a new one (non thread-safe)."""
    if isinstance(bind, str):
        engine = utils.create_engine(
            bind, pool_pre_ping=pool_pre_ping, **engine_kwargs
        )
        bind = engine
    else:
        engine = bind.engine

    __ENGINE_REGISTRY[str(engine.url)] = engine
    return bind


def get_or_create(url: str, **engine_kwargs) -> Engine:
    """Get an engine from the registry or create it if does not exist."""
    if existing_engine := get(url=url, **engine_kwargs):
        return existing_engine

    with __LOCK:
        return register(url, **engine_kwargs)


def get(url: str, **engine_kwargs) -> typing.Optional[Engine]:
    with __LOCK:
        return __ENGINE_REGISTRY.get(url)
