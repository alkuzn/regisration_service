from fastapi import status
from fastapi.exceptions import HTTPException


class EmailExistsException(HTTPException):
    def __init__(self):
        status_code = status.HTTP_409_CONFLICT
        detail = "Email уже используется."
        super().__init__(status_code, detail)


class BadCodeException(HTTPException):
    def __init__(self):
        status_code = status.HTTP_409_CONFLICT
        detail = "Неверный код или вышло время."
        super().__init__(status_code, detail)


class DatabaseConnectionException(Exception):
    pass


class UserNotFound(HTTPException):
    def __init__(self):
        status_code = status.HTTP_400_BAD_REQUEST
        detail = "Пользователь не найден."
        super().__init__(status_code, detail)
