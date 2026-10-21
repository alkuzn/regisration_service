from datetime import UTC, datetime
from typing import Annotated
from uuid import uuid4

import jwt
from fastapi import APIRouter, BackgroundTasks, Body, Depends, Request, status
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse
from fastapi_limiter.depends import RateLimiter
from pyrate_limiter import Duration, Limiter, Rate
from sqlalchemy.ext.asyncio import AsyncSession

from auth_service.api.dependencies import gen_session_id, get_db, verify_code
from auth_service.api.exceptions import EmailExistsException
from auth_service.api.func import email_exists, get_user_by_email, save_code
from auth_service.api.schemes import (
    FinishLoginAnswer,
    FinishRegAnswer,
    PublicKeyAnswer,
    StartLoginAnswer,
    StartRegAnswer,
)
from auth_service.db.models import User
from auth_service.logging_s import AsyncLogger
from auth_service.schemes.schemes import RegisterData

logger = AsyncLogger(__name__)

router = APIRouter()


@router.post(
    "/start-registration",
    # dependencies=[Depends(RateLimiter(limiter=Limiter(Rate(100, Duration.SECOND * 5))))],
    response_model=StartRegAnswer,
    responses={
        status.HTTP_409_CONFLICT: {
            "description": "Конфликт: email уже зарегистрирован",
            "content": {
                "application/json": {
                    "example": {"detail": "Данный email уже зарегистрирован"}
                }
            },
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "Когда потеряно соединение с базой",
            "content": {
                "application/json": {
                    "example": {"detail": "Сервис недосупен. Повторите попытку позже"}
                }
            },
        },
    },
)
async def start_registration(
    bgtasks: BackgroundTasks,
    data: Annotated[RegisterData, Body()],
    session: Annotated[AsyncSession, Depends(get_db)],
    new_session_id: Annotated[str, Depends(gen_session_id)],
    request: Request,
):
    try:
        if await email_exists(session, data.email):
            raise EmailExistsException()
    except (TimeoutError, ConnectionError) as ex:
        await logger.error(f"Ошибка запроса с базе данных")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Сервис недоступен. Повторите попытку позже",
            headers={"Retry-After": "30"},
        )
    bgtasks.add_task(
        save_code, data.email, new_session_id, request.app.state.code_carrier
    )
    await logger.info(f"Процесс регистрации начался")
    return {"success": True, "sessionid": new_session_id}


@router.post(
    "/finish-registration",
    # dependencies=[Depends(RateLimiter(limiter=Limiter(Rate(100, Duration.SECOND * 5))))],
    response_model=FinishRegAnswer,
    status_code=202,
)
async def finish_registration(
    bgtasks: BackgroundTasks,
    cached_data: Annotated[dict, Depends(verify_code)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    user = User(email=cached_data["email"])
    try:
        session.add(user)
        await session.commit()
        await session.refresh(user)
    except Exception as ex:
        await logger.error(f"Ошибка при выполнении запроса к бд: {ex}")
    user_id = user.uuid
    if user_id:
        await logger.info(f"Пользователь {user_id} создан")
        return {"success": True}
    else:
        await logger.info(f"Ошибка создания пользователя")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST, content={"success": False}
        )


@router.post(
    "/login",
    dependencies=[
        #    Depends(RateLimiter(limiter=Limiter(Rate(100, Duration.SECOND * 5))))
    ],
    response_model=StartLoginAnswer,
    responses={
        status.HTTP_404_NOT_FOUND: {
            "description": "пользователь с данным email не найден в базе",
            "content": {
                "application/json": {
                    "example": {"detail": "Данный email не зарегистрирован"}
                }
            },
        }
    },
)
async def login(
    bgtasks: BackgroundTasks,
    data: Annotated[RegisterData, Body()],
    session: Annotated[AsyncSession, Depends(get_db)],
    new_session_id: Annotated[str, Depends(gen_session_id)],
    request: Request,
):
    if not await email_exists(session, data.email):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": "Данный email не зарегистрирован."},
        )
    await logger.info(f"login started")
    bgtasks.add_task(
        save_code, data.email, new_session_id, request.app.state.code_carrier
    )
    return {"success": True, "sessionid": new_session_id}


@router.post(
    "/finish-login",
    # dependencies=[Depends(RateLimiter(limiter=Limiter(Rate(100, Duration.SECOND * 5))))],
    response_model=FinishLoginAnswer,
    status_code=202,
)
async def finish_login(
    bgtasks: BackgroundTasks,
    cached_data: Annotated[dict, Depends(verify_code)],
    session: Annotated[AsyncSession, Depends(get_db)],
    request: Request,
):

    user = await get_user_by_email(session, cached_data["email"])
    # if user.is_banned():
    #   return JSONResponse(
    #    status_code=status.HTTP_403_FORBIDDEN, content={"success": True, "msg": "Пользователь заблокирован"}
    # )
    jwt_headers = {}
    payload = {}
    state = request.app.state
    jwt_headers["kid"] = state.jwk.kid
    payload["exp"] = datetime.now(UTC) + state.jwt_timedelta
    payload["jti"] = str(uuid4())
    payload["user_id"] = str(user.uuid)
    token = jwt.encode(
        headers=jwt_headers,
        payload=payload,
        key=state.jwk.private.to_pem(),
        algorithm="RS256",
    )
    await logger.info(f"Пользователь вошёл: {cached_data["email"]}")
    return {"success": True, "token": token}


@router.get("/health")
async def health(request: Request):
    red = await request.app.state.redis.ping()
    red or await logger.error("Нет подключения к redis")
    # db =
    # db or await logger.error("Нет подключения к базе данных")
    return red


@router.get(
    "/public_key",
    description="Этот метод предоставляет публичный ключ другим сервисам.",
    response_model=PublicKeyAnswer,
)
async def public_key(request: Request):
    jwk_s = request.app.state.jwk  # TODO: имя jwk_s путает. поменяй
    data = {"keys": []}
    data["keys"].append({"use": "sig", "kid": jwk_s.kid, **jwk_s.public.to_dict()})
    return data
