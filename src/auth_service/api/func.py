from datetime import UTC, datetime, timedelta
from random import random

from cryptography.hazmat.primitives import serialization
from jose import jwk
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from auth_service.api.exceptions import UserNotFound
from auth_service.db.models import User
from auth_service.logging_s import AsyncLogger

logger = AsyncLogger(__name__)


class Jwk:
    kid = "123"  # TODO: Это надо переделать

    def __init__(self, keys_path):
        """
        keys_path - путь к папке где лежат два ключа public.key и private.key
        """
        with open(f"{keys_path}/public.key", "rb") as key_file:
            public_key = serialization.load_pem_public_key(key_file.read())
        self._public_key = jwk.construct(public_key, algorithm="RS256")

        with open(f"{keys_path}/private.key", "rb") as key_file:
            private_key = serialization.load_pem_private_key(
                key_file.read(), password=None
            )
        self._private_key = jwk.construct(private_key, algorithm="RS256")

    @property
    def public(self):
        return self._public_key

    @property
    def private(self):
        return self._private_key


class CodeCarrier:
    def __init__(self, redis: Redis):
        self.redis = redis

    async def save_code(self, email: str, code: str, sessionid: str) -> None:
        key = f"auth_service:{sessionid[:10]}"
        await self.redis.hset(
            key,
            mapping={
                "email": email,
                "code": code,
                "sessionid": sessionid,
            },
        )
        await self.redis.expireat(key, datetime.now(UTC) + timedelta(minutes=2))
        await logger.info(f"Код {code} отправлен в брокеру")

    async def verify_auth_code(self, sessionid: str, code: str) -> dict | None:
        key = f"auth_service:{sessionid[:10]}"
        resp = await self.redis.hgetall(key)
        if resp and resp["sessionid"] == sessionid and resp["code"] == code:
            await self.redis.delete(key)
            return resp
        return None


async def email_exists(session: AsyncSession, email: str) -> bool | None:
    stmt = select(User.uuid).where(User.email == email)
    result = await session.execute(stmt)
    return result.scalar() is not None


async def save_code(email: str, sessionid: str, code_carrier: CodeCarrier):
    code = str(random())[2:6]
    await code_carrier.save_code(email, code, sessionid)
    ##?????


async def get_user_by_email(session: AsyncSession, email: str) -> User:
    """Возвращает пользователя или выбрасывает исключение"""
    stmt = select(User).where(User.email == email)
    res = await session.execute(stmt)
    try:
        user = res.scalar_one()
    except NoResultFound:
        raise UserNotFound
    return user
