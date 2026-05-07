from datetime import datetime
from enum import IntEnum
import jwt
from config import JWT_SECRET_KEY, JWT_ACCESS_TOKEN_EXPIRE_MINUTES, JWT_REFRESH_TOKEN_EXPIRE_MINUTES, JWT_ALGORITHM
from plugins import Singleton


class TokenExpiredException(Exception):
    pass


class TokenChoice(IntEnum):
    ACCESS_TOKEN = 1
    REFRESH_TOKEN = 2


class TokenHandler(Singleton):
    def encode_token(self, user_id: str, choice: TokenChoice) -> str:
        if choice == TokenChoice.ACCESS_TOKEN:
            exp = datetime.now() + JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        else:
            exp = datetime.now() + JWT_REFRESH_TOKEN_EXPIRE_MINUTES
        payload = dict(
            iss=user_id,
            sub=str(choice.value),
            exp=int(exp.timestamp())
        )
        return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

    def make_tokens(self, user_id: str) -> dict[str, str]:
        access_token = self.encode_token(user_id, TokenChoice.ACCESS_TOKEN)
        refresh_token = self.encode_token(user_id, TokenChoice.REFRESH_TOKEN)
        tokens = dict(
            access_token=access_token,
            refresh_token=refresh_token
        )
        return tokens

    def update_token(self, user_id: str) -> str:
        return self.encode_token(user_id, TokenChoice.ACCESS_TOKEN)

    def decode_access_token(self, token: str) -> str:
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            if payload['sub'] != str(TokenChoice.ACCESS_TOKEN.value):
                raise ValueError('Token类型错误')
            return payload['iss']
        except jwt.ExpiredSignatureError:
            raise TokenExpiredException('Access Token已过期')
        except jwt.InvalidTokenError:
            raise ValueError('Access Token不可用')

    def decode_refresh_token(self, token: str) -> str:
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            if payload['sub'] != str(TokenChoice.REFRESH_TOKEN.value):
                raise ValueError('Token类型错误')
            return payload['iss']
        except jwt.ExpiredSignatureError:
            raise ValueError('Refresh Token已过期')
        except jwt.InvalidTokenError:
            raise ValueError('Refresh Token不可用')
