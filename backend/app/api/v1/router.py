from fastapi import APIRouter

from app.api.v1 import calculation_session, dashboard, trades

api_router = APIRouter()
api_router.include_router(calculation_session.router)
api_router.include_router(dashboard.router)
api_router.include_router(trades.router)
