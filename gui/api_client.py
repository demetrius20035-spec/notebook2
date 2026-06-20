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

    # ── аутентификация ──
    def login(self, username: str, password: str, remember: bool = False) -> None:
        data = self._post(
            "/api/v1/auth/login",
            json={"username": username, "password": password, "remember_me": remember},
            auth=False,
        )
        self._token = data["access_token"]

    @property
    def authenticated(self) -> bool:
        return self._token is not None

    def logout(self) -> None:
        self._token = None

    # ── запросы домена ──
    def list_tickets(self, status: str | None = None) -> list[dict]:
        params = {"status": status} if status else None
        return self._get("/api/v1/tickets", params=params)

    def get_ticket(self, ticket_id: int) -> dict:
        return self._get(f"/api/v1/tickets/{ticket_id}")

    def ticket_history(self, ticket_id: int) -> list[dict]:
        return self._get(f"/api/v1/tickets/{ticket_id}/history")

    def add_measurement(self, ticket_id: int, payload: dict) -> dict:
        return self._post(f"/api/v1/tickets/{ticket_id}/measurements", json=payload)

    def list_providers(self) -> dict:
        return self._get("/api/v1/ai/providers")

    def diagnose(self, payload: dict) -> dict:
        return self._post("/api/v1/ai/diagnose", json=payload)

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
                headers=self._headers(auth), timeout=60,
            )
        except requests.RequestException as exc:
            raise APIError(f"Сеть недоступна: {exc}") from exc

        body = resp.json() if resp.content else {}
        if resp.status_code >= 400:
            detail = body.get("detail") or body.get("error", {}).get("message") or resp.text
            raise APIError(str(detail), resp.status_code)
        return body.get("data", body)
