#!/bin/sh
set -e

# Wait for PostgreSQL to be ready (up to 60s)
if echo "$DATABASE_URL" | grep -q "postgresql"; then
    echo "Waiting for PostgreSQL..."
    for i in $(seq 1 30); do
        python3 -c "
import sys
try:
    import psycopg2
    import os
    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    conn.close()
    sys.exit(0)
except Exception as e:
    sys.exit(1)
" && echo "PostgreSQL ready!" && break
        echo "  Attempt $i/30..."
        sleep 2
    done
fi

# Clone skills if GITHUB_TOKEN set
SKILLS_DIR="/app/skills/cdb-skills"
if [ ! -d "$SKILLS_DIR" ] && [ -n "$GITHUB_TOKEN" ]; then
    echo "Cloning cdb-skills..."
    mkdir -p /app/skills
    git clone https://x-access-token:${GITHUB_TOKEN}@github.com/BIK-GmbH/cdb-skills.git "$SKILLS_DIR" 2>&1 || echo "WARNING: Could not clone cdb-skills"
fi

exec uvicorn backend.main:app --host 0.0.0.0 --port "${PORT:-8000}"
