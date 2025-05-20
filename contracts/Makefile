.PHONY: all compile_contracts verify_contracts install install-dev lint isort black autopep8 format mypy clean release update_gas_costs dist upload-pypi

all: verify_contracts install

compile_contracts:
	python scripts/compile_contracts.py

verify_contracts:
	python scripts/verify_contracts.py

update_gas_costs:
	pytest "gatecoin_contracts/tests/test_print_gas.py::test_print_gas" -s

install:
	uv pip install -e .

install-dev:
	uv pip install -e ".[dev]"

LINT_FILES = gatecoin_contracts/

ISORT_PARAMS = --ignore-whitespace --settings-path ./ gatecoin_contracts/

BLACK_PARAMS = gatecoin_contracts/

lint: mypy
	black --check --diff $(BLACK_PARAMS)
	flake8 $(LINT_FILES)
	pylint $(LINT_FILES)
	isort $(ISORT_PARAMS) --check-only

mypy:
	mypy $(LINT_FILES)

isort:
	isort $(ISORT_PARAMS)

black:
	black $(BLACK_PARAMS)

format: isort black

clean:
	rm -rf build/ dist/ *.egg-info/ .eggs .pytest_cache __pycache__

release: clean verify_contracts dist upload-pypi

dist:
	uv pip install build
	python -m build

upload-pypi:
	uv pip install twine
	twine upload dist/*
