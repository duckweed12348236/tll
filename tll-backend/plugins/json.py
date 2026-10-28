from typing import Any
from decimal import Decimal

import orjson


def extend(obj: Any) -> Any:
    if isinstance(obj, Decimal):
        return format(obj, ".2f")
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def dump(obj: Any) -> bytes:
    return orjson.dumps(obj, extend)


def load(obj: bytes | str) -> Any:
    return orjson.loads(obj)
