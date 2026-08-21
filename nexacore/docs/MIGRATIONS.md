# Migrations

## Status: CREATED, NOT EXECUTED

`alembic/versions/0001_initial_schema.py` was **hand-authored**, not
generated via `alembic revision --autogenerate`, because this sandbox has
no live database connection and no SQLAlchemy installed (no PyPI access —
see `docs/SETUP.md`). It has **never been run** against a real Postgres
instance.

## What was actually verified (programmatically, in this sandbox)
- **Table count**: 22 `op.create_table()` calls in the migration exactly
  match the 22 models registered in `app/db/base.py`.
- **Column completeness**: for every one of the 22 tables, every
  `Mapped[...]` attribute in the model file has a corresponding
  `sa.Column(...)` in the migration, and vice versa — checked with a
  script that parses both the model source and the migration source and
  diffs the column name sets. Zero mismatches found.
- **Foreign keys**: every `ForeignKey("table.column")` string in every
  model matches a `sa.ForeignKey("table.column")` in the migration —
  checked the same way. Zero mismatches.
- **Unique constraints**: `unique=True` columns (`users.email`,
  `sources.source_key`, `lead_score_rules.rule_key`) match exactly between
  models and migration.
- **Table creation order** respects FK dependencies (verified by manual
  read-through — Tier 0 tables with no FKs, then Tier 1 tables depending
  only on Tier 0, then Tier 2 depending on Tier 1).

## What was NOT verified (requires a real database)
- Whether `alembic upgrade head` actually succeeds against a fresh Postgres
  instance without error.
- Whether the resulting schema is byte-for-byte what SQLAlchemy's
  `Base.metadata.create_all()` would produce (the real gold-standard check).
- Whether `alembic downgrade base` cleanly reverses everything.
- Index behavior, cascade behavior, or any runtime constraint enforcement.

## To verify locally
```bash
cd backend
source .venv/bin/activate   # after following docs/SETUP.md
# point DATABASE_URL at a throwaway/fresh Postgres database
alembic upgrade head
# then, as a cross-check against the ORM's own view of the schema:
python -c "
from app.db.session import engine
from app.db.base import Base
from sqlalchemy import inspect
inspector = inspect(engine)
tables = set(inspector.get_table_names())
expected = set(Base.metadata.tables.keys())
print('Missing:', expected - tables)
print('Extra:', tables - expected)
"
alembic downgrade base   # confirm clean teardown
```
Report back what (if anything) fails — most likely candidates for a
hand-authored migration to get wrong are `server_default` syntax quirks
(e.g. `sa.true()`/`sa.false()` vs a dialect-specific boolean literal) or a
FK ordering issue Postgres is stricter about than this review process caught.
