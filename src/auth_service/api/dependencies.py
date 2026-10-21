import secrets
from typing import Annotated

from fastapi import Body, Request

from auth_service.api.exceptions import BadCodeException, DatabaseConnectionException
from auth_service.db import SessionMaker
from auth_service.logging_s import AsyncLogger

logger = AsyncLogger(__name__)


async def get_db(request: Request):
    sess = SessionMaker()
    try:
        yield sess
    except ConnectionRefusedError as ex:
        msg = f"Ошибка подключения к базе данных"
        await logger.error(f"{msg}: {str(ex)}")
        raise DatabaseConnectionException(msg)
    finally:
        await sess.close()


async def verify_code(
    code: Annotated[str, Body()],
    sessionid: Annotated[str, Body()],
    request: Request,
):
    result = await request.app.state.code_carrier.verify_auth_code(sessionid, code)
    if not result:
        raise BadCodeException()
    return result


def get_code_carrier(request: Request):
    return request.app.state.code_carrier


def gen_session_id():
    return secrets.token_hex(32)
