"""Vercel serverless Python entrypoint when deployed with apps/web as Root Directory."""
import os
import sys
from pathlib import Path

# Traverse upward to find the repository root containing apps/api
current = Path(__file__).resolve()
repo_root = current.parent
for parent in current.parents:
    if (parent / "apps" / "api").is_dir():
        repo_root = parent
        break

api_dir = repo_root / "apps" / "api"
if str(api_dir) not in sys.path:
    sys.path.insert(0, str(api_dir))

from controlcheck.main import create_app  # noqa: E402

db_path = os.getenv("CONTROLCHECK_DB") or ("/tmp/controlcheck.db" if os.getenv("VERCEL") else None)
app = create_app(db_path=db_path)
