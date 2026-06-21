# Evidence Engine — developer entry points.
# All targets assume the venv at .venv (created by `make setup`).

PY := .venv/bin/python
PIP := .venv/bin/pip

.PHONY: help setup run test typecheck reproduce clean

help:
	@echo "make setup      - create venv and install pinned dependencies"
	@echo "make run        - run the full pipeline (Phase-0 audit + evidence object)"
	@echo "make test       - run the test suite (pytest)"
	@echo "make typecheck  - run mypy over the package"
	@echo "make reproduce  - run twice and assert byte-identical evidence output"
	@echo "make clean      - remove generated outputs and caches"

setup:
	python3 -m venv .venv
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt -r requirements-dev.txt
	$(PIP) install -e .

run:
	$(PY) -m evidence_engine config.yaml

test:
	.venv/bin/pytest

typecheck:
	.venv/bin/mypy src/evidence_engine || true

reproduce:
	$(PY) -m evidence_engine config.yaml
	cp outputs/evidence_object.json outputs/_run1.json
	$(PY) -m evidence_engine config.yaml
	@diff -q outputs/_run1.json outputs/evidence_object.json \
		&& echo "REPRODUCIBLE: byte-identical across runs" \
		|| (echo "NOT REPRODUCIBLE" && exit 1)

clean:
	rm -rf outputs/*.json outputs/_run*.json .pytest_cache **/__pycache__
