.PHONY: dev dev-backend dev-frontend test test-backend build clean

dev: dev-backend dev-frontend

dev-backend:
	cd backend && source ../.venv/bin/activate && uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000 &

dev-frontend:
	cd frontend && npm run dev &

test: test-backend

test-backend:
	source .venv/bin/activate && python -m pytest backend/tests/ -v

build:
	cd frontend && npm run build

clean:
	rm -rf frontend/dist frontend/node_modules .venv backend/__pycache__ backend/**/__pycache__

docker-up:
	docker compose up --build

docker-down:
	docker compose down
