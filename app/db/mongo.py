from pymongo import MongoClient
from pymongo.database import Database

from app.core.config import settings


class MongoManager:
    client: MongoClient | None = None
    db: Database | None = None


mongo_manager = MongoManager()


def connect_to_mongo() -> None:
    mongo_manager.client = MongoClient(settings.mongo_uri)
    mongo_manager.db = mongo_manager.client[settings.mongo_db_name]


def close_mongo_connection() -> None:
    if mongo_manager.client:
        mongo_manager.client.close()
    mongo_manager.client = None
    mongo_manager.db = None


def get_db() -> Database:
    if mongo_manager.db is None:
        raise RuntimeError("Database is not connected.")
    return mongo_manager.db

