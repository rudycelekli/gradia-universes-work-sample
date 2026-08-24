.PHONY: setup test reproduce verify study-a frontier axes cost-capped public-boundary all

setup:
	python3 -m venv .venv
	.venv/bin/pip install -e '.[dev]'

test:
	.venv/bin/pytest -q
	.venv/bin/ruff check src tests
	.venv/bin/mypy --strict src tests

reproduce:
	.venv/bin/gradia-universe run

verify:
	.venv/bin/gradia-universe verify
	.venv/bin/gradia-universe study-a-verify
	.venv/bin/gradia-universe frontier-verify
	.venv/bin/gradia-universe axes-verify

study-a:
	.venv/bin/gradia-universe study-a-build

frontier:
	.venv/bin/gradia-universe frontier-build

axes:
	.venv/bin/python -m gradia_universes.axis_candidates build

cost-capped:
	.venv/bin/gradia-universe cost-capped-verify

public-boundary:
	.venv/bin/gradia-universe verify-public

all: test verify cost-capped public-boundary
