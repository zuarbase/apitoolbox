# pylint: disable=protected-access,unnecessary-dunder-call

from apitoolbox.registry import Registry


def test_registry_cleanup_thread_stops_on_del():
    registry = Registry(cleanup_interval_in_sec=0.1)

    assert not registry._stop_event.is_set()
    assert registry._cleanup_thread.is_alive()

    registry.__del__()
    # del registry

    assert registry._stop_event.is_set()
    assert not registry._cleanup_thread.is_alive()
