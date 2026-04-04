#!/bin/sh
# Start immediately - PostgreSQL retry is handled by pool_pre_ping in the app
exec uvicorn backend.main:app --host 0.0.0.0 --port "${PORT:-8000}"
