import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")

PORT = int(os.environ.get("PORT", 80))

SQLITE_DB_PATH = os.environ.get("SQLITE_DB_PATH", "/data/weesht.db")
