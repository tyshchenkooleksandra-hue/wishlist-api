"""Перевірка health-ендпоінта. База тут навмисно заборонена."""

from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine

from main import app


def test_health_does_not_touch_database(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("/health не має звертатися до бази")

    monkeypatch.setattr(Engine, "connect", forbidden)

    # Без `with`: lifespan не запускається, отже таблиці не створюються й база не потрібна.
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
