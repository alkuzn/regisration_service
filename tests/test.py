from time import sleep

import httpx2
import psycopg
import pytest
import redis

from auth_service.config import settings


class MailService:
    def __init__(self, redis):
        self.redis = redis

    def get_code(self, sessionid):
        key = f"auth_service:{sessionid[:10]}"
        return self.redis.hget(f"{key}", "code")


@pytest.fixture(scope="session")
def db_connection():
    with psycopg.connect(**settings.db.model_dump()) as conn:
        yield conn


@pytest.fixture(scope="session", autouse=True)
def kkk(db_connection):
    yield
    with db_connection.cursor() as cursor:
        res = cursor.execute("delete from users;")
        # print(res.fetchone())


@pytest.fixture
def sync_httpx_client():
    with httpx2.Client() as cli:
        yield cli


@pytest.fixture
def mail_service():

    red = redis.from_url(settings.redis.url, decode_responses=True)
    assert red.ping(), "Нет подключения к redis."
    yield MailService(red)
    red.close()


@pytest.mark.parametrize(
    "email",
    [
        "user@ssaaddds.com",
        "user@ssdddds.com",
        "user@ssddddfs.com",
        "uasdfser@sssdfdddds.com",
        "user@ssdddds.codm",
    ],
)
def test_flow(sync_httpx_client, mail_service, db_connection, email):

    cli = sync_httpx_client
    BASE_URL = f"http://{settings.app.host}:{settings.app.port}"

    resp = cli.post(
        f"{BASE_URL}/start-registration",
        json={"email": email},
    )
    assert resp.status_code == 200
    sleep(0.1)
    answer = resp.json()

    code = mail_service.get_code(answer["sessionid"])

    resp = cli.post(
        f"{BASE_URL}/finish-registration",
        json={"sessionid": answer["sessionid"], "code": code},
    )
    assert resp.status_code == 202
    sleep(0.1)
    with db_connection.cursor() as cursor:
        res = cursor.execute("SELECT * FROM users WHERE email = %s;", (email,))
        assert res.fetchone()

    resp = cli.post(f"{BASE_URL}/login", json={"email": email})
    assert resp.status_code == 200
    sleep(0.1)
    answer = resp.json()

    code = mail_service.get_code(answer["sessionid"])

    resp = cli.post(
        f"{BASE_URL}/finish-login",
        json={"sessionid": answer["sessionid"], "code": code},
    )
    assert resp.status_code == 202


@pytest.mark.parametrize(
    "email",
    [
        "use1r@ssaaddds.com",
    ],
)
def test_bad_registration(sync_httpx_client, mail_service, db_connection, email):
    """Проверяется случай, когда токен запрашивается на регистрацию, а применяется в finish-login"""

    cli = sync_httpx_client
    BASE_URL = f"http://{settings.app.host}:{settings.app.port}"

    resp = cli.post(
        f"{BASE_URL}/start-registration",
        json={"email": email},
    )
    assert resp.status_code == 200
    sleep(0.1)
    answer = resp.json()

    code = mail_service.get_code(answer["sessionid"])

    resp = cli.post(
        f"{BASE_URL}/finish-login",
        json={"sessionid": answer["sessionid"], "code": code},
    )
    with db_connection.cursor() as cursor:
        res = cursor.execute("SELECT * FROM users WHERE email = %s;", (email,))
        assert not res.fetchone()
    assert resp.status_code == 400
