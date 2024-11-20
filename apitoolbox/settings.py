from enum import Enum


class DBRegistryRemoveItemStrategyEnum(str, Enum):
    DEFAULT = "default"
    DISPOSE_ENGINE = "dispose_engine"


DB_REGISTRY_CLEANUP_INTERVAL = None
DB_REGISTRY_ITEM_TTL = None
DB_REGISTRY_REFRESH_ON_GET = False
DB_REGISTRY_REMOVE_ITEM_STRATEGY_ENUM = (
    DBRegistryRemoveItemStrategyEnum.DEFAULT
)
