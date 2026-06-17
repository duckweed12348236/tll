from typing import Any
from decimal import Decimal

import orjson


def handle_unknown_type(obj: Any) -> Any:
    if isinstance(obj, Decimal):
        return format(obj, ".2f")
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def serialize(obj: Any) -> bytes:
    return orjson.dumps(obj, handle_unknown_type)


def deserialize(obj: bytes | str) -> Any:
    return orjson.loads(obj)
