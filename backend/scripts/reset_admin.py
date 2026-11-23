"""Reset the built-in admin password (for a fresh server install).

Usage (from the server, with the EMIS image):
    docker compose -f docker-compose.server.yml --profile init-db run --rm init-db \
        python scripts/reset_admin.py

Set NEW_ADMIN_PASSWORD in the environment to choose a different password.
"""

import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from app import models  # noqa: E402,F401
from app.config import get_settings  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import User  # noqa: E402
from app.utils.security import hash_password  # noqa: E402

db.init(get_settings())
password = os.getenv("NEW_ADMIN_PASSWORD", "ChangeThisPassword123!")
user = db.session.query(User).filter_by(username="admin").first()
if user is None:
    raise SystemExit("No user with username 'admin' exists. Run init-db first.")
user.password_hash = hash_password(password)
user.must_change_password = False
db.session.commit()
print(f"Admin password reset to: {password}")
