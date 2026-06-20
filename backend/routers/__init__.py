"""FastAPI-роутеры RepairExpert AI."""
from backend.routers import ai, auth, clients, components, tickets

ALL_ROUTERS = [auth.router, clients.router, tickets.router, ai.router, components.router]

__all__ = ["ALL_ROUTERS"]
