from __future__ import annotations

import os

from utils.repository import DataRepository

_repo: DataRepository | None = None


def get_repository() -> DataRepository:
    global _repo
    if _repo is None:
        backend = os.getenv("DATA_BACKEND", "json").lower()
        if backend == "json":
            from utils.data_json import JsonRepository

            _repo = JsonRepository()
        else:
            raise ValueError(f"지원하지 않는 DATA_BACKEND: {backend!r}")
    return _repo
