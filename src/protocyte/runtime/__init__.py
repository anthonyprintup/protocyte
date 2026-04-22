from __future__ import annotations

from functools import lru_cache
from importlib import resources


@lru_cache(maxsize=None)
def _read_runtime_text(name: str) -> str:
    return resources.files(__package__).joinpath(name).read_text(encoding="utf-8")


def runtime_files(prefix: str = "protocyte/runtime") -> dict[str, str]:
    normalized = prefix.strip("/") or "protocyte/runtime"
    return {
        f"{normalized}/runtime.hpp": _read_runtime_text("runtime.hpp"),
    }
