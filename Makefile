SHELL := /bin/bash

include apps/app/Makefile

.PHONY: install_venv
install_venv:
	python3.11 -m pip install -U pip && \
	poetry -V | grep "Poetry (version 1.8.2)" || (echo "Error: Poetry is not version 1.8.2. Aborting!" && exit 1) && \
	poetry env use python3.11 && \
	poetry install --all-extras && \
	poetry run pre-commit install

.PHONY: lint
lint:
	poetry run pre-commit run --all-files

.PHONY: test_app
test_app:
	poetry run pytest apps/app

.PHONY: test_core_llm
test_core_llm:
	poetry run pytest libs/core  -m "llm"

.PHONY: test_core_unit
test_core_unit:
	poetry run pytest libs/core -m "not llm"

.PHONY: test_core
test_core: test_core_unit test_core_llm

.PHONY: test_connectors
test_connectors:
	poetry run pytest libs/connectors

.PHONY: test_common
test_common:
	poetry run pytest libs/common

.PHONY: test_unit
test_unit: \
	test_core_unit \
	test_connectors \
	test_common \
	test_app

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
