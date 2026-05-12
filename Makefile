.PHONY: dev dev-backend dev-frontend build test

dev:
	docker compose up -d db
	cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload --port 8000 &
	cd frontend && npm install && npm run dev &
	wait

dev-backend:
	cd backend && uvicorn app.main:app --reload --port 8000

dev-frontend:
	cd frontend && npm run dev

build:
	docker compose build

test:
	cd backend && pytest -v
	cd frontend && npm test