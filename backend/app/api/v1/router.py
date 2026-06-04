from fastapi import APIRouter

from app.api.v1 import auth, audit_logs, calculation_session, client_quotes, clients, dashboard, engineer_session, estimator, integrations, products, rate_rules, reports, settings, trades, users

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
api_router.include_router(client_quotes.router)
api_router.include_router(integrations.eworks.router)
