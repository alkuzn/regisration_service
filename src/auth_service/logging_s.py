import sys
from contextvars import ContextVar
from logging import Filter, StreamHandler, basicConfig, getLogger
from logging.config import dictConfig

from aiologger import Logger
from aiologger.filters import Filter as AsyncFilter
from aiologger.formatters.base import Formatter
from aiologger.handlers.streams import AsyncStreamHandler

request_id_contextvar = ContextVar("request_id")  # TODO: Пока так, но потом переделай


class RequestIdFilter(Filter):
    def __init__(self, request_id: ContextVar, name="request_id"):
        self.request_id = request_id
        super().__init__(name)

    def set_request_id(self, request_id):
        self.request_id.set(request_id)

    def filter(self, record):
        record.request_id = self.request_id.get("no-id")
        return True


class AsyncRequestIdFilter(AsyncFilter):
    def __init__(self, request_id: ContextVar, name=""):
        self.request_id = request_id
        super().__init__(name)

    def filter(self, record):
        record.request_id = self.request_id.get("no-id")
        return True


def AsyncLogger(name: str):
    lg = Logger(name=name)
    hand = AsyncStreamHandler(
        level="INFO", formatter=Formatter("%(asctime)s; %(request_id)s; %(msg)s;")
    )
    lg.add_filter(AsyncRequestIdFilter(request_id_contextvar))
    lg.add_handler(hand)
    return lg


# TODO: Добавить форматтер для обычного логгера
