.PHONY: setup test reproduce verify study-a frontier axes cost-capped alignment public-boundary paper-numbers all

setup:
	python3 -m venv .venv
	.venv/bin/pip install -e '.[dev]'

test:
	.venv/bin/pytest -q
	.venv/bin/ruff check src tests scripts/verify_paper_numeric_claims.py
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

alignment:
	.venv/bin/python scripts/verify_four_judge_alignment.py

public-boundary:
	.venv/bin/gradia-universe verify-public

paper-numbers:
	$(MAKE) -C paper conditionally-approved
	.venv/bin/python scripts/verify_paper_numeric_claims.py

all: test verify cost-capped alignment public-boundary paper-numbers
