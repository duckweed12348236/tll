from typing import Any

import aiohttp
from fastapi import HTTPException, status

from config import GATEWAY_PORT, SERVER_HOST

gateway_url = f"http://{SERVER_HOST}:{GATEWAY_PORT}"
timeout = aiohttp.ClientTimeout(total=10)


async def send(method: str,
               path: str,
               token: str | None = None,
               params: dict[str, Any] | None = None,
               json: dict[str, Any] | None = None) -> Any:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.request(
                    method,
                    f"{gateway_url}{path}",
                    headers=headers,
                    params=params,
                    json=json
            ) as response:
                payload = await response.json(content_type=None)
                if response.status >= status.HTTP_400_BAD_REQUEST:
                    detail = payload.get("detail") if isinstance(payload, dict) else payload
                    raise HTTPException(response.status, detail or "用户服务不可用")
                return payload
    except aiohttp.ClientError as error:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, f"用户服务不可用: {error}")


async def authenticate(token: str) -> dict[str, Any]:
    return await send("GET", "/user/me", token=token)
