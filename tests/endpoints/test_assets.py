import os
import tempfile
import asyncio
from pathlib import Path

import pytest
from apitoolbox import endpoints


@pytest.fixture(scope="function", name="temp_dir")
def temp_dir_fixture():
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture(scope="function", name="loop")
def loop_fixture():
    return asyncio.get_event_loop()


def test_assets_list(loop, temp_dir):
    file1 = os.path.join(temp_dir, "file1")
    file2 = os.path.join(temp_dir, ".file2")
    symlink1 = os.path.join(temp_dir, "symlink1")

    Path(file1).touch()
    Path(file2).touch()
    Path(symlink1).symlink_to(file1)

    endpoint = endpoints.AssetManagerEndpoint(temp_dir)

    results = loop.run_until_complete(endpoint.list_assets("/"))
    assert len(results) == 1

    result = results[0]
    for key in ("atime", "ctime", "mtime"):
        value = result.pop(key)
        assert value and isinstance(value, str)

    assert result == {
        "id": endpoint.generate_id("/file1"),
        "name": "file1",
        "type": "file",
        "size": 0
    }


def test_assets_bad_path(loop, temp_dir):
    endpoint = endpoints.AssetManagerEndpoint(temp_dir)

    with pytest.raises(ValueError):
        loop.run_until_complete(endpoint.list_assets("."))


def test_assets_external_path(loop, temp_dir):
    endpoint = endpoints.AssetManagerEndpoint(temp_dir)

    with pytest.raises(FileNotFoundError):
        loop.run_until_complete(endpoint.list_assets("/foo/../../bar"))


def test_assets_list_subdir(loop, temp_dir):
    dir1 = os.path.join(temp_dir, "dir1")
    os.makedirs(dir1)
    file1 = os.path.join(temp_dir, "dir1", "file1")
    Path(file1).touch()

    endpoint = endpoints.AssetManagerEndpoint(temp_dir)

    results = loop.run_until_complete(endpoint.list_assets("/"))
    assert len(results) == 1

    result = results[0]
    for key in ("atime", "ctime", "mtime"):
        value = result.pop(key)
        assert value and isinstance(value, str)

    assert result == {
        "id": endpoint.generate_id("/dir1"),
        "name": "dir1",
        "type": "directory"
    }


def test_assets_list_subdir_file(loop, temp_dir):
    dir1 = os.path.join(temp_dir, "dir1")
    os.makedirs(dir1)
    file1 = os.path.join(temp_dir, "dir1", "file1")
    Path(file1).touch()

    endpoint = endpoints.AssetManagerEndpoint(temp_dir)

    results = loop.run_until_complete(endpoint.list_assets("/dir1"))
    assert len(results) == 1

    for result in results:
        for key in ("atime", "ctime", "mtime"):
            value = result.pop(key)
            assert value and isinstance(value, str)

    assert results == [
        {
            "id": endpoint.generate_id("/dir1/file1"),
            "name": "file1",
            "type": "file",
            "size": 0
        }
    ]
