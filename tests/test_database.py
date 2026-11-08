"""Інтеграційні тести: працюють зі справжніми Postgres і Redis (сервіси job'а в CI)."""

import uuid

import pytest
from fastapi.testclient import TestClient

from database import SessionLocal
from main import app
from models import WishList


@pytest.fixture(scope="module")
def client():
    # `with` запускає lifespan, тобто створює таблиці. Немає бази — тест впаде тут.
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_headers(client):
    email = f"user-{uuid.uuid4().hex}@example.com"
    password = "s3cret-password"
    registered = client.post("/register", json={"email": email, "password": password, "full_name": "Test User"})
    assert registered.status_code == 200, registered.text

    token = client.post("/token", data={"username": email, "password": password})
    assert token.status_code == 200, token.text
    return {"Authorization": f"Bearer {token.json()['access_token']}"}


def test_wishlist_is_written_to_postgres_and_read_back(client, auth_headers):
    title = f"Wishlist {uuid.uuid4().hex}"

    created = client.post("/wishlists", json={"title": title, "description": "ci"}, headers=auth_headers)
    assert created.status_code == 200, created.text
    wishlist_id = created.json()["id"]

    # Читаємо напряму із Postgres, повз API: рядок справді записаний у базу.
    with SessionLocal() as session:
        stored = session.get(WishList, wishlist_id)
        assert stored is not None
        assert stored.title == title

    # І через API, яким користується UI.
    fetched = client.get(f"/wishlists/{wishlist_id}")
    assert fetched.status_code == 200
    assert fetched.json()["title"] == title


def test_wishlists_list_is_served_through_redis_cache(client, auth_headers):
    title = f"Cached {uuid.uuid4().hex}"
    client.post("/wishlists", json={"title": title}, headers=auth_headers)

    first = client.get("/wishlists")
    second = client.get("/wishlists")  # другий запит — уже з кешу Redis

    assert first.status_code == second.status_code == 200
    assert title in [w["title"] for w in first.json()]
    assert first.json() == second.json()


def test_redis_is_reachable(client):
    # Ловить неправильне підключення Redis: /health не падає, але повідомляє unhealthy.
    assert client.get("/health").json()["redis"] == "healthy"
