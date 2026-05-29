from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import AppError, error_response
from app.core.logging import configure_application_insights, configure_logging


@asynccontextmanager
async def lifespan(_app: FastAPI):
    configure_logging()
    configure_application_insights()
    yield


app = FastAPI(title="Optimal Estimate Calculator API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)


@app.exception_handler(AppError)
async def app_error_handler(_request: Request, exc: AppError):
    return JSONResponse(status_code=exc.status_code, content=error_response(exc.code, exc.message, exc.details))


@app.get("/health")
def health():
    return {
        "status": "ok",
        "environment": settings.environment,
        "storage_backend": settings.storage_backend,
        "run_seed": settings.effective_run_seed,
        "frontend_url": settings.frontend_url or settings.cors_origin_list[0] if settings.cors_origin_list else None,
    }


app.include_router(api_router, prefix=settings.api_v1_prefix)
