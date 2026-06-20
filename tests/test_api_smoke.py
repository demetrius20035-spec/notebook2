"""Сквозной смоук-тест API на SQLite в памяти.

Проверяет основной рабочий поток без внешних сервисов (MariaDB/Qdrant/LLM):
логин → клиент → устройство → тикет → измерение → смена статуса → дашборд.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.core.database import get_db
from backend.core.security import hash_password
from backend.main import app
from backend.models import Base, DeviceType, User
from backend.models.enums import UserRole


@pytest.fixture
def client(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    with TestingSession() as db:
        db.add(
            User(
                username="admin",
                password_hash=hash_password("admin"),
                full_name="Админ",
                role=UserRole.ADMIN,
            )
        )
        db.add(DeviceType(name="Ноутбук"))
        db.commit()

    def _override():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()


def _token(client: TestClient) -> str:
    resp = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin"})
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["access_token"]


def test_full_repair_flow(client):
    headers = {"Authorization": f"Bearer {_token(client)}"}

    # me
    me = client.get("/api/v1/users/me", headers=headers).json()["data"]
    assert me["role"] == "admin"

    # клиент
    cl = client.post(
        "/api/v1/clients", headers=headers, json={"full_name": "Иван Петров", "phone": "+700001"}
    ).json()["data"]
    assert cl["id"]

    # устройство
    dt = client.get("/api/v1/device-types", headers=headers).json()["data"][0]
    dev = client.post(
        "/api/v1/devices",
        headers=headers,
        json={
            "client_id": cl["id"],
            "device_type_id": dt["id"],
            "manufacturer": "Lenovo",
            "model_name": "ThinkPad T14",
            "platform": "NM-D221",
        },
    ).json()["data"]
    assert dev["id"]

    # тикет
    ticket = client.post(
        "/api/v1/tickets",
        headers=headers,
        json={
            "client_id": cl["id"],
            "device_id": dev["id"],
            "problem_description": "Не включается, нет дежурных напряжений",
        },
    ).json()["data"]
    assert ticket["ticket_number"].startswith("РМ-")
    tid = ticket["id"]

    # измерение со статусом FAIL (норма 5, измерено 0)
    meas = client.post(
        f"/api/v1/tickets/{tid}/measurements",
        headers=headers,
        json={"line_name": "+5VALW", "value_measured": 0.0, "value_norm": 5.0},
    ).json()["data"]
    assert meas["status"] == "fail"

    # смена статуса new → diagnostics
    st = client.post(
        f"/api/v1/tickets/{tid}/status", headers=headers, json={"status": "diagnostics"}
    )
    assert st.status_code == 200, st.text
    assert st.json()["data"]["status"] == "diagnostics"

    # недопустимый переход diagnostics → delivered → 409
    bad = client.post(
        f"/api/v1/tickets/{tid}/status", headers=headers, json={"status": "delivered"}
    )
    assert bad.status_code == 409

    # дашборд
    dash = client.get("/api/v1/analytics/dashboard", headers=headers).json()["data"]
    assert dash["clients_total"] == 1
    assert dash["tickets_active"] >= 1


def test_login_rejects_bad_password(client):
    resp = client.post("/api/v1/auth/login", json={"username": "admin", "password": "nope"})
    assert resp.status_code == 401


def test_unauthorized_without_token(client):
    assert client.get("/api/v1/tickets").status_code in (401, 403)
