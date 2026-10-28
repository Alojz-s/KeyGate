import os

from app.core.config import ROOT_DIR

if not (ROOT_DIR / ".env").exists():
    os.environ.setdefault(
        "DATABASE_URL", "postgresql+psycopg://keygate:keygate@localhost:5432/keygate"
    )
