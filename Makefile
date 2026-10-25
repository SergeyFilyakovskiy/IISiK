.PHONY: install sync lint format test health

install:
	uv sync --all-packages
	uv run pre-commit install

sync:
	uv sync --all-packages

lint:
	uv run pre-commit run --all-files

format:
	uv run ruff format .
	uv run ruff check --fix .

test:
	uv run pytest

run-graphql:
	uv run --package graphql-api graphql-api

run-identity:
	uv run --package identity-service uvicorn identity_service.main:app --reload --port 8001

run-catalog:
	uv run --package catalog-service uvicorn catalog_service.main:app --reload --port 8002

run-scheduling:
	uv run --package scheduling-service uvicorn scheduling_service.main:app --reload --port 8003

run-booking:
	uv run --package booking-service uvicorn booking_service.main:app --reload --port 8004

run-payment:
	uv run --package payment-service uvicorn payment_service.main:app --reload --port 8005

run-review:
	uv run --package review-service uvicorn review_service.main:app --reload --port 8006
