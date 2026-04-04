#!/bin/sh

# Wait for PostgreSQL if using postgres URL
if echo "${DATABASE_URL}" | grep -q "postgresql"; then
    echo "Waiting for PostgreSQL to be ready..."
    MAX=30
    COUNT=0
    until python3 -c "
import sys, os
try:
    import psycopg2
    conn = psycopg2.connect(os.environ.get('DATABASE_URL',''))
    conn.close()
    sys.exit(0)
except Exception as e:
    print(f'Not ready: {e}', file=sys.stderr)
    sys.exit(1)
" 2>/dev/null; do
        COUNT=$((COUNT + 1))
        if [ $COUNT -ge $MAX ]; then
            echo "PostgreSQL not available after ${MAX} attempts, starting anyway..."
            break
        fi
        echo "  Waiting... ($COUNT/$MAX)"
        sleep 3
    done
    echo "PostgreSQL ready!"
fi

# Clone skills if needed
SKILLS_DIR="/app/skills/cdb-skills"
if [ ! -d "$SKILLS_DIR" ] && [ -n "$GITHUB_TOKEN" ]; then
    echo "Cloning cdb-skills..."
    mkdir -p /app/skills
    git clone "https://x-access-token:${GITHUB_TOKEN}@github.com/BIK-GmbH/cdb-skills.git" "$SKILLS_DIR" 2>&1 || echo "WARNING: Could not clone cdb-skills"
fi

exec uvicorn backend.main:app --host 0.0.0.0 --port "${PORT:-8000}"
