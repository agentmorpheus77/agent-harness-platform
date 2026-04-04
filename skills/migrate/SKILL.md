---
name: migrate
description: Use when the user wants to run, validate, preview, or rollback PostgreSQL database migrations safely
version: 0.1.0
---

# Migrate

Safe PostgreSQL database migrations with dry-run, validation, and rollback.

Migrations are numbered `.sql` files with `-- migrate:up` and `-- migrate:down` sections. Applied migrations are tracked in a `_schema_migrations` table.

## Migration file format

```sql
-- migrate:up
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL
);

-- migrate:down
DROP TABLE users;
```

Files must be named with a numeric prefix: `001_create_users.sql`, `002_add_index.sql`.

## Tools

### migrate
Run database migrations in one of four modes.

**Call:**
```bash
~/.cdb-skills/venv/bin/python {SKILL_DIR}/tools/migrate.py --mode <mode> --migrations-dir <path> [--database-url <url>] [--steps <n>]
```

**Parameters:**
| Parameter | Required | Description |
|-----------|----------|-------------|
| --mode | Yes | validate, dry-run, apply, or rollback |
| --migrations-dir | Yes | Path to directory with numbered .sql files |
| --database-url | No | PostgreSQL connection string (default: $DATABASE_URL) |
| --steps | No | Number of migrations to rollback (default: 1) |

**Modes:**
| Mode | What it does | Needs DB |
|------|-------------|----------|
| validate | Check files for duplicates, missing sections, empty SQL | No |
| dry-run | Show pending migrations without executing | Yes |
| apply | Apply pending migrations, each in its own transaction | Yes |
| rollback | Reverse last N migrations using their DOWN sections | Yes |

**Environment variables:**
| Variable | Description |
|----------|-------------|
| DATABASE_URL | PostgreSQL connection string (e.g., `postgresql://user:pass@localhost:5432/mydb`) |

**Examples:**
```bash
# Validate migration files (no DB needed)
~/.cdb-skills/venv/bin/python {SKILL_DIR}/tools/migrate.py --mode validate --migrations-dir ./migrations

# Preview what would be applied
~/.cdb-skills/venv/bin/python {SKILL_DIR}/tools/migrate.py --mode dry-run --migrations-dir ./migrations

# Apply pending migrations
~/.cdb-skills/venv/bin/python {SKILL_DIR}/tools/migrate.py --mode apply --migrations-dir ./migrations

# Rollback last 2 migrations
~/.cdb-skills/venv/bin/python {SKILL_DIR}/tools/migrate.py --mode rollback --migrations-dir ./migrations --steps 2
```

## When to use
- Running or previewing database schema changes
- Validating migration files before deploying
- Rolling back a failed or unwanted migration
- Checking which migrations are pending

## When NOT to use
- For Neo4j/graph database changes (use graph-inspect or Cypher directly)
- For data backfills or seed scripts (run those separately)
- For ORM-managed migrations (use Alembic/Django directly)
