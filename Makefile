.PHONY: install sync generate-proto lint format test health

PROTO_FILES := $(wildcard proto/*/v1/*.proto)

install:
	uv sync --all-packages
	uv run pre-commit install

sync:
	uv sync --all-packages

generate-proto:
	uv run python -m grpc_tools.protoc -Iproto \
		--python_out=packages/proto-generated/src \
		--grpc_python_out=packages/proto-generated/src \
		$(PROTO_FILES)

lint:
	uv run pre-commit run --all-files

format:
	uv run ruff format .
	uv run ruff check --fix .

test:
	uv run pytest

run-graphql:
	PYTHONPATH=services/graphql-api/src:packages/shared/src:packages/proto-generated/src \
		uv run --package graphql-api uvicorn graphql_api.main:app --reload --port 4000

run-identity:
	PYTHONPATH=services/identity-service/src:packages/shared/src:packages/proto-generated/src \
		uv run --package identity-service uvicorn identity_service.main:app --reload --port 8001

run-catalog:
	uv run --package catalog-service python -m catalog_service.main

run-scheduling:
	uv run --package scheduling-service python -m scheduling_service.main

run-booking:
	uv run --package booking-service python -m booking_service.main

run-payment:
	uv run --package payment-service python -m payment_service.main

run-review:
	uv run --package review-service python -m review_service.main

run-notification:
	uv run --package notification-service python -m notification_service.main

run-analytics:
	uv run --package analytics-service python -m analytics_service.main
