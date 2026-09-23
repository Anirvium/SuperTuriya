PYTHON ?= python3.12
VENV := .venv
VENV_PY := $(VENV)/bin/python
VENV_PIP := $(VENV)/bin/pip
KERNEL_ID := piyusha1234/notebook5326562b0c
TOKEN_FILE := .kaggle/access_token
KAGGLE := KAGGLE_API_TOKEN=$$(cat $(TOKEN_FILE)) $(VENV)/bin/kaggle
GAMES ?= ls20,vc33,ft09
STEPS ?= 40

.PHONY: help setup test doctor list-games cache local-smoke build-smoke build-model \
	build-repair verify push first-kaggle-test kaggle-model status pull-output _check-token

help:
	@echo "One workflow: develop/test here -> build dist/kaggle -> push the same notebook to Kaggle"
	@echo ""
	@echo "  make setup               Create the isolated Python 3.12 environment"
	@echo "  make test                Run the ARC package tests"
	@echo "  make cache               Cache public games for offline local runs"
	@echo "  make local-smoke         Run the non-model agent on public games"
	@echo "  make build-smoke         Build the first RTX/Kaggle validation notebook"
	@echo "  make first-kaggle-test   Build + upload the first validation version"
	@echo "  make build-model         Build Qwen 3.8 27B FP8 competition candidate"
	@echo "  make kaggle-model        Build + upload the model candidate"
	@echo "  make status              Check the existing Kaggle notebook run"

setup:
	$(PYTHON) -m venv $(VENV)
	$(VENV_PIP) install --upgrade pip
	$(VENV_PIP) install -r requirements.txt

test:
	PYTHONPATH=. $(VENV_PY) -m unittest discover -s tests -v

doctor:
	PYTHONPATH=. $(VENV_PY) -m superturiya_arc doctor

list-games:
	PYTHONPATH=. $(VENV_PY) -m superturiya_arc list

cache:
	PYTHONPATH=. $(VENV_PY) -m superturiya_arc cache --games "$(GAMES)"

local-smoke:
	@run_dir="results/local-smoke-$$(date -u +%Y%m%dT%H%M%SZ)"; \
	PYTHONPATH=. $(VENV_PY) -m superturiya_arc run \
		--config configs/smoke.json --games "$(GAMES)" --max-actions "$(STEPS)" \
		--output "$$run_dir"; \
	PYTHONPATH=. $(VENV_PY) -m superturiya_arc verify "$$run_dir"

build-smoke:
	PYTHONPATH=. $(VENV_PY) scripts/build_release.py --profile smoke

build-model:
	PYTHONPATH=. $(VENV_PY) scripts/build_release.py --profile competition

build-repair:
	PYTHONPATH=. $(VENV_PY) scripts/build_release.py --profile repair

verify:
	PYTHONPATH=. $(VENV_PY) -m superturiya_arc verify-build dist/kaggle

_check-token:
	@if [ ! -s "$(TOKEN_FILE)" ]; then \
		echo "Missing arc-agi/$(TOKEN_FILE). Save your Kaggle API token there as one line."; \
		echo "Create it at https://www.kaggle.com/settings (API -> Create New Token)."; \
		exit 1; \
	fi

push: _check-token verify
	PYTHONPATH=. KAGGLE_API_TOKEN=$$(cat $(TOKEN_FILE)) $(VENV_PY) -m superturiya_arc push dist/kaggle

first-kaggle-test: build-smoke push

kaggle-model: build-model push

status: _check-token
	$(KAGGLE) kernels status $(KERNEL_ID)

pull-output: _check-token
	@output_dir="results/kaggle-$$(date -u +%Y%m%dT%H%M%SZ)"; \
	mkdir -p "$$output_dir"; \
	$(KAGGLE) kernels output $(KERNEL_ID) -p "$$output_dir"; \
	echo "Downloaded to $$output_dir"
