from __future__ import annotations

import abc
import logging
import threading
import time
import typing as t


logger = logging.getLogger(__name__)
T = t.TypeVar("T")


class RegistryItem:
    def __init__(
        self,
        value: T,
        ttl: float | None = None,
        close_callback: t.Callable[[T], None] | None = None,
    ) -> None:
        self.value = value
        self.ttl = ttl
        self.expiration_time: float | None = time.time() + ttl if ttl else None
        self._close_callback = close_callback

    def is_expired(self) -> bool:
        if not self.expiration_time:
            return False

        return time.time() > self.expiration_time

    def refresh_expiry(self) -> None:
        """Refresh the expiration time based on the original TTL."""
        if not self.ttl:
            return

        self.expiration_time = time.time() + self.ttl

    def close(self) -> bool:
        if not self._close_callback:
            return True

        return self._close_callback(self)


class RemoveItemStrategyBase(abc.ABC):
    @abc.abstractmethod
    def remove(self, registry: Registry[T], key: t.Hashable) -> bool:
        """
        Thread-safe method to remove an item from the registry.

        This method assumes that a lock is already used in the client
        of this object to ensure thread safety.
        """


class CloseItemOnRemoveStrategy(RemoveItemStrategyBase):
    def remove(self, registry: Registry[T], key: t.Hashable) -> bool:
        item = registry.get_item(key)
        if not item:
            logger.debug(f"Item with key {key} not found")
            return False

        logger.debug(f"Closing item with key: {key}")
        is_closed_successfully = item.close()
        if item.close():
            logger.debug(f"Item with key {key} closed")
        else:
            logger.debug(f"Failed to close item with key: {key}")
        return is_closed_successfully


class RemoveItemStrategy(RemoveItemStrategyBase):
    def remove(self, registry: Registry[T], key: t.Hashable) -> bool:
        item = registry.get_item(key)
        if not item:
            logger.debug(f"Item with key {key} not found")
            return False

        registry._remove_item(key)  # pylint: disable=protected-access
        logger.debug(f"Item with key {key} closed and removed")
        return True


class CompositeRemoveItemStrategy(RemoveItemStrategyBase):
    def __init__(
        self,
        strategies: list[RemoveItemStrategyBase],
        break_on_failure: bool = True,
    ) -> None:
        self.strategies = strategies
        self.break_on_failure = break_on_failure

    def remove(self, registry: Registry[T], key: t.Hashable) -> bool:
        for strategy in self.strategies:
            result = strategy.remove(registry, key)
            if not result and self.break_on_failure:
                return False
        return True


class Registry(t.Generic[T]):
    """A thread-safe registry with TTL for items."""
    def __init__(
        self,
        cleanup_interval_in_sec: float | None = None,
        refresh_item_ttl_on_get: bool = False,
        remove_item_strategy: RemoveItemStrategyBase | None = None,
    ) -> None:
        self._items: dict[t.Hashable, RegistryItem[T]] = {}
        self._lock = threading.RLock()
        self._refresh_on_get = refresh_item_ttl_on_get
        self._cleanup_interval = cleanup_interval_in_sec
        self._remove_item_strategy = (
            remove_item_strategy or
            CompositeRemoveItemStrategy(
                strategies=[
                    CloseItemOnRemoveStrategy(), RemoveItemStrategy(),
                ],
                break_on_failure=True,
            )
        )
        if self._cleanup_interval:
            self._cleanup_thread = threading.Thread(
                target=self._cleanup_task, daemon=True
            )
            self._cleanup_thread.start()

    def set(
        self,
        key: t.Hashable,
        value: T,
        ttl: float | None = None,
        close_callback: t.Callable[[T], None] | None = None,
    ) -> None:
        if ttl and not self._cleanup_interval:
            logger.warning(
                "TTL is set but cleanup interval is not, "
                "expired items will not be removed"
            )

        with self._lock:
            logger.debug(f"Setting item with key: {key}")
            self._items[key] = RegistryItem(
                value=value, ttl=ttl, close_callback=close_callback
            )

    def get(self, key: t.Hashable) -> T | None:
        with self._lock:
            item = self.get_item(key)
            if not item:
                logger.debug(f"Item with key {key} not found")
                return None

            if item.is_expired():
                logger.debug(f"Item with key {key} is expired")
                self.remove(key)
                if not self.get_item(key):
                    return None

            if self._refresh_on_get:
                logger.debug(f"Refreshing item with key: {key}")
                item.refresh_expiry()  # Refresh TTL if the flag is set

            logger.debug(f"Returning item with key: {key}")
            return item.value

    def get_item(self, key: t.Hashable) -> RegistryItem[T] | None:
        with self._lock:
            logger.debug(f"Getting item with key: {key}")
            return self._items.get(key)

    def remove(self, key):
        with self._lock:
            self._remove_item_strategy.remove(self, key)

    def copy_to(self, other: Registry[T]) -> None:
        # pylint: disable=protected-access
        with self._lock:
            for key, item in self._items.items():
                other.set(
                    key=key,
                    value=item.value,
                    ttl=item.ttl,
                    close_callback=item._close_callback,
                )

    def _remove_item(self, key: t.Hashable) -> None:
        with self._lock:
            self._items.pop(key, None)
            logger.debug(f"Item with key {key} removed")

    def _cleanup_task(self):
        """Periodically clean up expired items."""
        while True:
            time.sleep(self._cleanup_interval)
            self._cleanup()

    def _cleanup(self):
        with self._lock:
            logger.debug("Cleaning up expired items")
            expired_keys = [
                key for key, item in self._items.items()
                if item.is_expired()
            ]
            logger.debug(f"Expired keys: {expired_keys}")
            for key in expired_keys:
                self.remove(key)
            logger.debug("Finished cleaning up expired items")

    def __len__(self):
        """Get the number of items in the registry."""
        with self._lock:
            return len(self._items)
