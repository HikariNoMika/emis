"""Create an empty EMIS schema plus seed data — no imported readings.

Use this when deploying fresh and you do not want to copy the local SQLite
database to the server. Data can be imported later through the normal upload
flow in the web interface.

Run from the backend directory, or via the `init-db` compose profile:
    docker compose -f docker-compose.server.yml --profile init-db run --rm --build init-db
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from app import models  # noqa: E402,F401 - register tables in Base.metadata
from app.config import get_settings  # noqa: E402
from app.extensions import db  # noqa: E402

DATABASE_URL = get_settings().DATABASE_URL
if not DATABASE_URL.startswith("postgres"):
    raise SystemExit(
        f"init_db is for the server PostgreSQL database, got: {DATABASE_URL}"
    )

db.init(get_settings())
db.create_all()

from app.services.accomplishment_service import seed_defaults  # noqa: E402
from seed import (  # noqa: E402
    ensure_core_data,
    seed_admin,
    seed_reference_station,
    seed_settings,
)

ensure_core_data()
admin = seed_admin()
seed_reference_station()
seed_settings(admin)
seed_defaults()
db.session.commit()
db.session.remove()

print("Database initialized: schema created, catalogue and admin account seeded.")
