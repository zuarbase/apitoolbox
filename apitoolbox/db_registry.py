"""
Database engines registry.

The registry is a single source of shared sqlalchemy engines.

NOTE: there are both thread-safe and non thread-safe functions.
"""
from sqlalchemy.engine import Connectable, Engine
from sqlalchemy.engine.url import make_url

from apitoolbox import utils
from apitoolbox.registry import (
    CloseItemOnRemoveStrategy,
    Registry,
    RemoveItemStrategyBase,
)
from apitoolbox.settings import (
    DBRegistryRemoveItemStrategyEnum,
    DB_REGISTRY_CLEANUP_INTERVAL, DB_REGISTRY_ITEM_TTL,
    DB_REGISTRY_REFRESH_ON_GET, DB_REGISTRY_REMOVE_ITEM_STRATEGY_ENUM,
)


__ENGINE_REGISTRY = None
__REGISTRY_ITEM_TTL = None


def register(
    bind: str | Connectable, pool_pre_ping=True, **engine_kwargs
) -> Engine:
    """Register an engine or create a new one (non thread-safe)."""
    assert __ENGINE_REGISTRY is not None, "Registry not initialized"

    engine_kwargs.setdefault("pool_pre_ping", pool_pre_ping)
    if isinstance(bind, str):
        engine = utils.create_engine(bind, **engine_kwargs)
        bind = engine
    else:
        engine = bind.engine

    registry_key = str(make_url(str(engine.url)))


    __ENGINE_REGISTRY.set(
        key=registry_key,
        value=engine,
        ttl=__REGISTRY_ITEM_TTL,
        close_callback=lambda registry_item: (
            (_engine := registry_item.value) and
            (
                not hasattr(_engine.pool, "checkedout") or
                _engine.pool.checkedout() == 0
            ) and
            (_engine.dispose() or True)
        ),
    )
    return bind


def get_or_create(url: str, **engine_kwargs) -> Engine:
    """Get an engine from the registry or create it if does not exist."""
    url = str(make_url(str(url))) if url else url
    if existing_engine := get(url=url, **engine_kwargs):
        return existing_engine

    return register(url, **engine_kwargs)


def get(  # pylint: disable=unused-argument
    url: str, **engine_kwargs
) -> Engine | None:
    return __ENGINE_REGISTRY.get(url)


def recreate_db_registry(
    cleanup_interval_in_sec=DB_REGISTRY_CLEANUP_INTERVAL,
    refresh_item_ttl_on_get=DB_REGISTRY_REFRESH_ON_GET,
    remove_item_strategy_enum=DB_REGISTRY_REMOVE_ITEM_STRATEGY_ENUM,
    registry_item_ttl_in_sec=DB_REGISTRY_ITEM_TTL,
):
    global __ENGINE_REGISTRY  # pylint: disable=global-statement
    global __REGISTRY_ITEM_TTL  # pylint: disable=global-statement
    previous_registry = __ENGINE_REGISTRY

    new_registry = Registry[Engine](
        cleanup_interval_in_sec=cleanup_interval_in_sec,
        refresh_item_ttl_on_get=refresh_item_ttl_on_get,
        remove_item_strategy=(
            _remove_item_strategy_factory(remove_item_strategy_enum)
        ),
    )
    if previous_registry:
        previous_registry.copy_to(new_registry)

    __ENGINE_REGISTRY = new_registry
    __REGISTRY_ITEM_TTL = registry_item_ttl_in_sec


def _remove_item_strategy_factory(
    strategy_enum: DBRegistryRemoveItemStrategyEnum,
) -> RemoveItemStrategyBase | None:
    if strategy_enum == DBRegistryRemoveItemStrategyEnum.DEFAULT:
        return None
    if strategy_enum == DBRegistryRemoveItemStrategyEnum.DISPOSE_ENGINE:
        # dispose engine, but do not remove it from the registry
        return CloseItemOnRemoveStrategy()

    raise ValueError(f"Invalid strategy: {strategy_enum}")


# Initialize the registry
recreate_db_registry()
