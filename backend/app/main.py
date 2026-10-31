import asyncio
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import settings
from app.core.exceptions import AppError
from app.database.mongodb import close_mongo_connection, connect_to_mongo, ping_db
from app.database.sync_mongodb import close_sync_client
from app.services.tracking_service import recover_after_restart
from app.workers.manager import manager

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("app.request")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    await recover_after_restart()
    yield
    await asyncio.to_thread(manager.stop_all)  # close open sessions cleanly
    close_sync_client()
    await close_mongo_connection()


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    if not request.url.path.endswith("/stream"):  # streams are long-lived; skip
        logger.info("%s %s -> %d (%.1f ms)", request.method, request.url.path, response.status_code,
                    (time.perf_counter() - start) * 1000)
    return response


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


app.include_router(api_router)


@app.get("/health", tags=["system"])
async def health():
    db_ok = await ping_db()
    return {
        "status": "ok" if db_ok else "degraded",
        "app": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
        "database": "connected" if db_ok else "unreachable",
    }
