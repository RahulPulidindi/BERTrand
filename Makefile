# Everything here except `smoke` runs offline: no API key, no model calls.
# Re-running the experiments themselves needs an OpenRouter key; see scripts/ and the README.

PY ?= .venv/bin/python

.PHONY: help install test lint data figures results all smoke

help:
	@echo "make install   create .venv and install the package with dev tools"
	@echo "make test      unit tests, known-answer checks and mock end-to-end runs"
	@echo "make figures   blog and README figures, from data/*.csv (exported from the logs first if missing)"
	@echo "make data      data/*.csv, from the raw logs in logs/"
	@echo "make results   every phase's results.md and paper figures, from the raw logs"
	@echo "make lint      ruff"
	@echo "make all       test, data, figures and results"
	@echo "make smoke     one 5-round market with three cheap models, about 1 cent (needs OPENROUTER_API_KEY in .env)"

install:
	python3 -m venv .venv
	$(PY) -m pip install -e ".[dev]"

test:
	$(PY) -m pytest -q

lint:
	$(PY) -m ruff check .

data:
	$(PY) -m analysis.export --logs logs --out data

figures:
	test -f data/phase4_markets.csv || $(PY) -m analysis.export --logs logs --out data
	$(PY) -m analysis.blog_figures --data data --out figures/blog

results:
	{ $(PY) -m analysis.hypotheses logs/run1; printf '\n---\n\n'; \
	  $(PY) -m analysis.hypotheses logs/run1 --exclude qwen; printf -- '---\n'; \
	  $(PY) -m analysis.report logs/run1 --out figures/run1; \
	  $(PY) -m analysis.monitor_eval logs/run1 --text logs/run1/monitor_probe.jsonl logs/run1/monitor_control.jsonl; \
	} > logs/run1/results.md
	$(PY) -m analysis.phase2 logs/run2 --monitor logs/run2/monitor.jsonl --sellers logs/run2/sellers.jsonl --out figures/run2 > logs/run2/results.md
	$(PY) -m analysis.phase3 --out figures/run3 > logs/run3/results.md
	$(PY) -m analysis.phase4 --out figures/run4 > logs/run4/results.md

all: test data figures results

smoke:
	set -a; . ./.env; set +a; .venv/bin/inspect eval inspect_task/task.py --model none \
	  -T seller_models=openrouter/openai/gpt-6-luna,openrouter/qwen/qwen3-235b-a22b-2507,openrouter/anthropic/claude-haiku-5.5 \
	  -T reasoning_effort=none -T conditions=board -T episodes=1 -T rounds=5 --log-dir logs/smoke-local
