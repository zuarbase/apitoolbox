""" Asset manager implementation """
import os
import logging
import hashlib
from typing import Any, Dict, List

from apitoolbox import tz

logger = logging.getLogger(__name__)


class AssetManagerEndpoint:
    """ Class-based endpoint for an Asset Manager """

    def __init__(
            self,
            document_root: str
    ):
        self.document_root = os.path.abspath(document_root)

    @staticmethod
    def generate_id(
            path: str
    ) -> str:
        """MD5 the path as a unique id"""
        encoded = hashlib.md5(path.encode("utf-8")).hexdigest()
        return encoded[0:8] + "-" + encoded[8:12] + "-" + encoded[12:16] +\
            "-" + encoded[16:20] + encoded[20:]

    @staticmethod
    def stat_time(
            timestamp: float
    ) -> str:
        """ Convert a stat time to a UTC datetime strimg """
        datetime = tz.datetime.utcfromtimestamp(timestamp)
        return datetime.isoformat()

    async def list_assets(
            self,
            path: str
    ) -> List[Dict[str, Any]]:
        """ List contents of 'path'"""
        if not path.startswith("/"):
            raise ValueError("Path must start with a forward slash '/'")
        path = path[1:]

        root_path = os.path.abspath(os.path.join(self.document_root, path))
        if not root_path.startswith(self.document_root):
            logger.warning("Attempting to access external path: %s", path)
            raise FileNotFoundError(path)

        result = []
        with os.scandir(root_path) as scanner:
            for entry in scanner:
                if entry.name.startswith(".") or entry.name.startswith("_"):
                    continue  # pragma: no cover

                data = {}
                stat_result = entry.stat()

                if entry.is_file(follow_symlinks=False):
                    data["type"] = "file"
                    data["size"] = stat_result.st_size
                elif entry.is_dir(follow_symlinks=False):
                    data["type"] = "directory"
                else:
                    continue  # pragma: no cover

                if path:
                    data["id"] = self.generate_id("/" + path + "/" + entry.name)
                else:
                    data["id"] = self.generate_id("/" + entry.name)
                data["name"] = entry.name

                data["atime"] = self.stat_time(stat_result.st_atime)
                data["mtime"] = self.stat_time(stat_result.st_mtime)
                data["ctime"] = self.stat_time(stat_result.st_ctime)

                result.append(data)

        return sorted(result, key=lambda x: x["name"])
