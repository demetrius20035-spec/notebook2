"""Тонкий клиент к FastAPI-бэкенду для GUI.

Использует requests (синхронно — удобно из Qt-слотов). Хранит JWT-токен
в памяти и подставляет его в заголовок Authorization.
"""
from __future__ import annotations

from typing import Any

import requests


class APIError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class APIClient:
    """Клиент REST API RepairExpert AI."""

    def __init__(self, base_url: str = "http://127.0.0.1:8077") -> None:
        self.base_url = base_url.rstrip("/")
        self._token: str | None = None
        self._session = requests.Session()
        self.current_user: dict | None = None

    # ── аутентификация ──
    def login(self, username: str, password: str, remember: bool = False) -> None:
        data = self._post(
            "/api/v1/auth/login",
            json={"username": username, "password": password, "remember_me": remember},
            auth=False,
        )
        self._token = data["access_token"]
        self.current_user = self._get("/api/v1/users/me")

    @property
    def authenticated(self) -> bool:
        return self._token is not None

    def logout(self) -> None:
        self._token = None
        self.current_user = None

    @property
    def role(self) -> str:
        return (self.current_user or {}).get("role", "")

    # ── пользователи ──
    def list_users(self) -> list[dict]:
        return self._get("/api/v1/users")

    # ── клиенты ──
    def list_clients(self, q: str | None = None) -> list[dict]:
        return self._get("/api/v1/clients", params={"q": q} if q else None)

    def create_client(self, payload: dict) -> dict:
        return self._post("/api/v1/clients", json=payload)

    def client_tickets(self, client_id: int) -> list[dict]:
        return self._get(f"/api/v1/clients/{client_id}/tickets")

    # ── справочники / устройства ──
    def list_device_types(self) -> list[dict]:
        return self._get("/api/v1/device-types")

    def list_manufacturers(self) -> list[dict]:
        return self._get("/api/v1/manufacturers")

    def create_device(self, payload: dict) -> dict:
        return self._post("/api/v1/devices", json=payload)

    # ── тикеты ──
    def list_tickets(self, status: str | None = None) -> list[dict]:
        return self._get("/api/v1/tickets", params={"status": status} if status else None)

    def get_ticket(self, ticket_id: int) -> dict:
        return self._get(f"/api/v1/tickets/{ticket_id}")

    def create_ticket(self, payload: dict) -> dict:
        return self._post("/api/v1/tickets", json=payload)

    def change_status(self, ticket_id: int, status: str) -> dict:
        return self._post(f"/api/v1/tickets/{ticket_id}/status", json={"status": status})

    def ticket_history(self, ticket_id: int) -> list[dict]:
        return self._get(f"/api/v1/tickets/{ticket_id}/history")

    def add_history(self, ticket_id: int, payload: dict) -> dict:
        return self._post(f"/api/v1/tickets/{ticket_id}/history", json=payload)

    def list_measurements(self, ticket_id: int) -> list[dict]:
        return self._get(f"/api/v1/tickets/{ticket_id}/measurements")

    def add_measurement(self, ticket_id: int, payload: dict) -> dict:
        return self._post(f"/api/v1/tickets/{ticket_id}/measurements", json=payload)

    def list_documents(self, ticket_id: int) -> list[dict]:
        return self._get(f"/api/v1/tickets/{ticket_id}/documents")

    def generate_document(self, ticket_id: int, document_type: str) -> dict:
        return self._post(
            f"/api/v1/tickets/{ticket_id}/documents", json={"document_type": document_type}
        )

    # ── компоненты ──
    def list_components(self, q: str | None = None) -> list[dict]:
        return self._get("/api/v1/components", params={"q": q} if q else None)

    def create_component(self, payload: dict) -> dict:
        return self._post("/api/v1/components", json=payload)

    def component_analogs(self, component_id: int) -> list[dict]:
        return self._get(f"/api/v1/components/{component_id}/analogs")

    # ── склад ──
    def list_inventory(self) -> list[dict]:
        return self._get("/api/v1/inventory")

    def upsert_inventory(self, payload: dict) -> dict:
        return self._post("/api/v1/inventory", json=payload)

    def inventory_move(self, payload: dict) -> dict:
        return self._post("/api/v1/inventory/moves", json=payload)

    def list_suppliers(self) -> list[dict]:
        return self._get("/api/v1/suppliers")

    # ── база знаний ──
    def list_knowledge(self, q: str | None = None) -> list[dict]:
        return self._get("/api/v1/knowledge", params={"q": q} if q else None)

    def create_knowledge(self, payload: dict) -> dict:
        return self._post("/api/v1/knowledge", json=payload)

    def get_knowledge(self, article_id: int) -> dict:
        return self._get(f"/api/v1/knowledge/{article_id}")

    # ── финансы ──
    def list_payments(self, ticket_id: int | None = None) -> list[dict]:
        return self._get(
            "/api/v1/finance/payments", params={"ticket_id": ticket_id} if ticket_id else None
        )

    def add_payment(self, payload: dict) -> dict:
        return self._post("/api/v1/finance/payments", json=payload)

    def revenue_report(self, days: int = 30) -> dict:
        return self._get("/api/v1/finance/report", params={"days": days})

    # ── аналитика ──
    def dashboard(self) -> dict:
        return self._get("/api/v1/analytics/dashboard")

    # ── AI ──
    def list_providers(self) -> dict:
        return self._get("/api/v1/ai/providers")

    def diagnose(self, payload: dict) -> dict:
        return self._post("/api/v1/ai/diagnose", json=payload)

    def ai_health(self, provider: str | None = None) -> dict:
        return self._get("/api/v1/ai/health", params={"provider": provider} if provider else None)

    # ── низкоуровневые helpers ──
    def _headers(self, auth: bool) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if auth and self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    def _get(self, path: str, params: dict | None = None) -> Any:
        return self._request("GET", path, params=params)

    def _post(self, path: str, json: dict | None = None, auth: bool = True) -> Any:
        return self._request("POST", path, json=json, auth=auth)

    def _request(self, method: str, path: str, *, json=None, params=None, auth=True) -> Any:
        url = f"{self.base_url}{path}"
        try:
            resp = self._session.request(
                method, url, json=json, params=params,
                headers=self._headers(auth), timeout=120,
            )
        except requests.RequestException as exc:
            raise APIError(f"Сеть недоступна: {exc}") from exc

        body = resp.json() if resp.content else {}
        if resp.status_code >= 400:
            detail = body.get("detail") or body.get("error", {}).get("message") or resp.text
            raise APIError(str(detail), resp.status_code)
        return body.get("data", body)
