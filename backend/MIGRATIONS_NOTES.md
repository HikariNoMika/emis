# Database migrations (Alembic / SQLAlchemy 2.0)

From the `backend/` folder:

```bash
alembic revision --autogenerate -m "Initial schema"
alembic upgrade head
alembic downgrade -1
alembic current
```

Alembic is configured in `alembic.ini`; `migrations/env.py` reads the database
URL from `DATABASE_URL` and uses `app.extensions.Base.metadata`, so every model
in `app/models/` is included automatically.

## TimescaleDB hypertable

`measurements` is converted into a hypertable by a migration containing:

```sql
CREATE EXTENSION IF NOT EXISTS timescaledb;
SELECT create_hypertable('measurements', 'observation_time', if_not_exists => TRUE);
```

`measurements` has a composite primary key `(id, observation_time)` and its
duplicate-prevention unique constraint also includes `observation_time`, which
is required by TimescaleDB.
