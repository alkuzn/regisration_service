PYTHON_RUN_M := PYTHONDONTWRITEBYTECODE=1 python3 -B -m 
UV_RUN_M := $(PYTHON_RUN_M) uv run -m

run: 
	$(UV_RUN_M) auth_service

run_in_docker:
	sudo docker compose down
	sudo docker compose up --build

migrate:
	$(UV_RUN_M) alembic -q check || $(UV_RUN_M) alembic revision --autogenerate && $(UV_RUN_M) alembic upgrade head

check:
	$(PYTHON_RUN_M) uv check
	
sync:
	$(PYTHON_RUN_M) uv sync

format:
	$(UV_RUN_M) isort .
	$(UV_RUN_M) black .
	
test:
	$(UV_RUN_M) pytest -s tests/test.py

before_commit: format check test
