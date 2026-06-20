"""FastAPI-роутеры RepairExpert AI."""
from backend.routers import (
    ai,
    analytics,
    auth,
    catalog,
    clients,
    components,
    finance,
    inventory,
    knowledge,
    tickets,
    users,
)

ALL_ROUTERS = [
    auth.router,
    users.router,
    clients.router,
    catalog.router,
    tickets.router,
    components.router,
    inventory.router,
    knowledge.router,
    finance.router,
    analytics.router,
    ai.router,
]

__all__ = ["ALL_ROUTERS"]
