#!/bin/sh
set -e

# Clone cdb-skills if GITHUB_TOKEN is set and skills don't exist yet
SKILLS_DIR="/app/skills/cdb-skills"

if [ ! -d "$SKILLS_DIR" ] && [ -n "$GITHUB_TOKEN" ]; then
  echo "Cloning cdb-skills..."
  mkdir -p /app/skills
  git clone https://x-access-token:${GITHUB_TOKEN}@github.com/BIK-GmbH/cdb-skills.git "$SKILLS_DIR" 2>&1 || echo "WARNING: cdb-skills clone failed, continuing without skills..."
fi

exec uvicorn backend.main:app --host 0.0.0.0 --port "${PORT:-8000}"
