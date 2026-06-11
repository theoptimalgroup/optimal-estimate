from fastapi import APIRouter

from app.api.v1 import admin, auth, audit_logs, calculation_session, client_quotes, clients, dashboard, engineer_session, estimator, integrations, manager, processed_quotes, products, quote_assignments, rate_rules, reports, settings, trades, users, voice
from app.api.v1 import eworks_sync

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(calculation_session.router)
api_router.include_router(engineer_session.router)
api_router.include_router(dashboard.router)
api_router.include_router(clients.router)
api_router.include_router(trades.router)
api_router.include_router(products.router)
api_router.include_router(rate_rules.router)
api_router.include_router(users.router)
api_router.include_router(audit_logs.router)
api_router.include_router(reports.router)
api_router.include_router(settings.router)
api_router.include_router(estimator.router)
api_router.include_router(manager.router)
api_router.include_router(admin.router)
api_router.include_router(client_quotes.router)
api_router.include_router(integrations.eworks.router)
api_router.include_router(eworks_sync.router)
api_router.include_router(quote_assignments.router)
api_router.include_router(processed_quotes.router)
api_router.include_router(voice.router)
