import secrets
from contextlib import asynccontextmanager
from datetime import timedelta

import redis.asyncio as redis
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from redis.exceptions import ConnectionError

from auth_service.api.exceptions import DatabaseConnectionException
from auth_service.api.func import CodeCarrier, Jwk
from auth_service.api.handles import router
from auth_service.config import settings
from auth_service.db.main import engine
from auth_service.logging_s import AsyncLogger, request_id_contextvar

logger = AsyncLogger(__name__)


@asynccontextmanager
async def life(app: FastAPI):
    try:
        app.state.jwk = Jwk(settings.app.key_path)
    except Exception as ex:
        await logger.error(f"При получении ключа возникла ошибка: {str(ex)}")
        exit()
    app.state.request_id = request_id_contextvar
    app.state.jwt_timedelta = timedelta(days=1)
    app.state.redis = redis.from_url(settings.redis.url, decode_responses=True)
    app.state.code_carrier = CodeCarrier(app.state.redis)
    try:
        await app.state.redis.ping()
    except ConnectionError as ex:
        await logger.error(f"Ошибка подключения к redis: {str(ex)}")
    yield
    await app.state.redis.close()
    await engine.dispose()  # Данные теряются?


app = FastAPI(
    title="Auth service",
    lifespan=life,
    **settings.fastapi.model_dump(),
)

app.include_router(router)


@app.exception_handler(RequestValidationError)
async def general_validation_handler(request: Request, ex: RequestValidationError):
    for err in ex.errors():
        match (err):
            case {"type": "value_error", "loc": ("body", field_name)}:
                msg = f"Невалидное поле {field_name}."
            case {"type": "missing", "loc": ("body", field_name)}:
                msg = f"Не указано поле {field_name}."
            case _:
                await logger.info(f"unknown error: {err}")
                msg = "Неизвестная ошибка"
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, content={"detail": msg}
    )


@app.exception_handler(DatabaseConnectionException)
async def han(request: Request, ex: DatabaseConnectionException):
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=str(ex)
    )


@app.middleware("http")
async def logger_mid(request: Request, callnext):
    request.app.state.request_id.set(secrets.token_hex(10))
    await logger.info(f"{request.headers['user-agent']}")
    response = await callnext(request)
    return response
