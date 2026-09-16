"""Vercel serverless Python entrypoint when deployed with apps/web as Root Directory."""
import os
import sys
from pathlib import Path

# Add current directory so bundled api/controlcheck is immediately available
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

# Also add apps/api if running from monorepo
for parent in [current_dir] + list(current_dir.parents):
    candidate = parent / "apps" / "api"
    if candidate.is_dir() and str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from controlcheck.main import create_app  # noqa: E402

db_path = os.getenv("CONTROLCHECK_DB") or ("/tmp/controlcheck.db" if os.getenv("VERCEL") else None)
app = create_app(db_path=db_path)
