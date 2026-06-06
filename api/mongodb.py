from functools import lru_cache

from django.conf import settings
from pymongo import MongoClient


@lru_cache(maxsize=1)
def get_client() -> MongoClient:
    config = settings.MONGODB_SETTINGS
    return MongoClient(
        config["URI"],
        tz_aware=True,
        serverSelectionTimeoutMS=config.get("SERVER_SELECTION_TIMEOUT_MS", 5000),
    )


@lru_cache(maxsize=1)
def get_database():
    config = settings.MONGODB_SETTINGS
    database_name = config.get("DATABASE")
    if not database_name:
        return get_client().get_default_database()
    return get_client()[database_name]


def get_collection(name: str):
    return get_database()[name]


def ping_database() -> bool:
    get_client().admin.command("ping")
    return True
