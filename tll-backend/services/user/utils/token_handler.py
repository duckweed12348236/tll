from datetime import UTC, datetime
from enum import IntEnum

import jwt

from services.user.config import JWT_SECRET_KEY, JWT_ACCESS_TOKEN_EXPIRE_MINUTES, JWT_REFRESH_TOKEN_EXPIRE_MINUTES, \
    JWT_ALGORITHM
from services.user.utils import Singleton


class TokenExpiredException(Exception):
    pass


class TokenChoice(IntEnum):
    ACCESS_TOKEN = 1
    REFRESH_TOKEN = 2


class TokenHandler(Singleton):
    def encode_token(self, user_id: str | int, choice: TokenChoice) -> str:
        if choice == TokenChoice.ACCESS_TOKEN:
            exp = datetime.now(UTC) + JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        else:
            exp = datetime.now(UTC) + JWT_REFRESH_TOKEN_EXPIRE_MINUTES
        payload = dict(
            iss=str(user_id),
            sub=str(choice.value),
            exp=int(exp.timestamp())
        )
        return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

    def make_tokens(self, user_id: str | int) -> dict[str, str]:
        access_token = self.encode_token(user_id, TokenChoice.ACCESS_TOKEN)
        refresh_token = self.encode_token(user_id, TokenChoice.REFRESH_TOKEN)
        tokens = dict(
            access_token=access_token,
            refresh_token=refresh_token
        )
        return tokens

    def update_token(self, user_id: str | int) -> str:
        return self.encode_token(user_id, TokenChoice.ACCESS_TOKEN)

    def decode_token(self, token: str, choice: TokenChoice) -> int:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        if payload.get("sub") != str(choice.value):
            raise ValueError("Token类型错误")
        issuer = payload.get("iss")
        if issuer is None:
            raise ValueError("Token缺少用户标识")
        return int(issuer)

    def decode_access_token(self, token: str) -> int:
        try:
            return self.decode_token(token, TokenChoice.ACCESS_TOKEN)
        except jwt.ExpiredSignatureError:
            raise TokenExpiredException("Access Token已过期")
        except jwt.InvalidTokenError:
            raise ValueError("Access Token不可用")

    def decode_refresh_token(self, token: str) -> int:
        try:
            return self.decode_token(token, TokenChoice.REFRESH_TOKEN)
        except jwt.ExpiredSignatureError:
            raise ValueError("Refresh Token已过期")
        except jwt.InvalidTokenError:
            raise ValueError("Refresh Token不可用")
