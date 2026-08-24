.PHONY: up down seed test lint logs

up:
	docker compose up --build

down:
	docker compose down -v

seed:
	docker compose exec api python -m scripts.seed

test:
	cd backend && pytest --cov=app --cov-report=term-missing

lint:
	cd backend && ruff check . && ruff format --check .

logs:
	docker compose logs -f api worker simulator
