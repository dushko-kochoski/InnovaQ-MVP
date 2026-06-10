import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import auth, templates, webhooks, workflows
from backend.config import settings
from backend.database.seed import seed_templates

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("innovaq")


@asynccontextmanager
async def lifespan(app: FastAPI):
    count = seed_templates()  # also runs create_all()
    logger.info("database ready, %s templates seeded", count)
    yield


app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG, lifespan=lifespan)

# Origins come from FRONTEND_URL (the deployed frontend). In DEBUG, the local
# dev origins are added too — both hostname spellings, because cookies only
# flow when frontend and API agree on the host (see DECISIONS.md D14).
_allowed_origins = {settings.FRONTEND_URL}
if settings.DEBUG:
    _allowed_origins |= {"http://localhost:3000", "http://127.0.0.1:3000"}
_allowed_origins = list(_allowed_origins)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "%s %s -> %s (%.1fms)",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response


app.include_router(auth.router)
app.include_router(webhooks.router)
app.include_router(workflows.router)
app.include_router(templates.router)


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok", "app": settings.APP_NAME}
