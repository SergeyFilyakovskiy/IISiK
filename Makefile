.PHONY: install sync generate-proto lint format test health

install:
	uv sync --all-packages
	uv run pre-commit install

sync:
	uv sync --all-packages

generate-proto:
	uv run python -m grpc_tools.protoc -Iproto \
		--python_out=packages/proto-generated/src \
		--grpc_python_out=packages/proto-generated/src \
		proto/identity/v1/identity.proto

lint:
	uv run pre-commit run --all-files

format:
	uv run ruff format .
	uv run ruff check --fix .

test:
	uv run pytest

run-graphql:
	PYTHONPATH=services/graphql-api/src:services/identity-service/src:services/catalog-service/src:services/scheduling-service/src:services/booking-service/src:services/payment-service/src:services/review-service/src:services/notification-service/src:services/analytics-service/src:packages/shared/src \
		uv run --package graphql-api uvicorn graphql_api.main:app --reload --port 4000

run-identity:
	PYTHONPATH=services/identity-service/src:packages/shared/src:packages/proto-generated/src \
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
