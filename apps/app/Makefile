SHELL := /bin/bash

CONTAINER_NAME ?= deep_next_app

.PHONY: app_run
app_run:
	poetry run python apps/app/deep_next/app/entrypoint_scheduled.py

.PHONY: app_docker_build
app_docker_build:
	docker build -t deep_next_app:latest -f apps/app/Dockerfile .

.PHONY: _app_docker_run
_app_docker_run:
	@if [ ! -f .env ]; then \
		echo "Error: .env file not found in $(shell pwd)"; \
		exit 1; \
	fi

	docker run -d \
		--name "$(CONTAINER_NAME)" \
		-v $(HOME)/.ssh:/root/.ssh:ro \
		-v $(shell pwd)/.env:/deep-next/.env:ro \
		deep_next_app:latest

	@echo -e 'Inspect logs:\ndocker logs -f $(CONTAINER_NAME)'

.PHONY: app_docker_run
app_docker_run: _assert_container_does_not_exist app_docker_build _app_docker_run

.PHONY: app_docker_stop
app_docker_stop:
	docker rm -f $(CONTAINER_NAME)

.PHONY: _assert_container_does_not_exist
_assert_container_does_not_exist:
	@if [ "$(shell docker ps -a --filter "name=$(CONTAINER_NAME)" --format '{{.Names}}')" = "$(CONTAINER_NAME)" ]; then \
		echo "Error: Container '$(CONTAINER_NAME)' already exists. Aborting..."; \
		exit 1; \
	fi
