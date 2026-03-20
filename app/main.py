from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.core.config import settings
from app.db.mongo import close_mongo_connection, connect_to_mongo, get_db
from app.routers.auth import router as auth_router
from app.routers.emergency import router as emergency_router
from app.routers.missing import router as missing_router
from app.routers.notifications import router as notifications_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    connect_to_mongo()
    db = get_db()

    db.users.create_index("email", unique=True)
    db.emergencies.create_index([("user_id", 1), ("timestamp", -1)])
    db.location_logs.create_index([("user_id", 1), ("time", -1)])
    db.missing_persons.create_index([("status", 1), ("time", -1)])
    db.sightings.create_index([("person_id", 1), ("timestamp", -1)])
    db.notifications.create_index([("user_id", 1), ("timestamp", -1)])

    yield
    close_mongo_connection()


app = FastAPI(title=settings.app_name, lifespan=lifespan)

if settings.cors_origins_list:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts_list)

app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(emergency_router, prefix=settings.api_prefix)
app.include_router(missing_router, prefix=settings.api_prefix)
app.include_router(notifications_router, prefix=settings.api_prefix)


@app.get("/")
def health() -> dict:
    return {"status": "ok", "app": settings.app_name}


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "healthy"}
