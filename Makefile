PYTHON ?= python
ACCEPTANCE_OUTPUT ?= build/architecture-acceptance.json

.PHONY: quality lint typecheck test acceptance security sealed-evidence package-smoke

quality: lint typecheck test acceptance security sealed-evidence

lint:
	$(PYTHON) -m ruff check beastbox/aliases.py beastbox/hashutil.py beastbox/logging_config.py \
		beastbox/continuity.py beastbox/durable.py beastbox/events.py beastbox/providers.py \
		beastbox/runtime_cli.py beastbox/swap_receipt.py scripts/run_architecture_acceptance.py \
		scripts/productization_receipt.py tests/test_durable_runtime.py tests/test_product_spine.py \
		tests/test_runtime_cli.py tests/test_swap_receipt.py tests/test_experimental_boundary.py

typecheck:
	$(PYTHON) -m mypy beastbox/logging_config.py beastbox/hashutil.py beastbox/aliases.py \
		beastbox/continuity.py beastbox/durable.py beastbox/events.py beastbox/providers.py \
		beastbox/cli.py beastbox/cypher/models.py beastbox/runtime_cli.py beastbox/swap_receipt.py \
		scripts/run_architecture_acceptance.py

test:
	mkdir -p build
	$(PYTHON) -m coverage run -m pytest --junitxml=build/junit.xml
	$(PYTHON) -m coverage report

acceptance:
	$(PYTHON) scripts/run_architecture_acceptance.py --output $(ACCEPTANCE_OUTPUT)

security:
	PYTHON=$(PYTHON) scripts/security-audit.sh

sealed-evidence:
	scripts/smoke/sealed-evidence-guard.sh

package-smoke:
	PYTHON=$(PYTHON) scripts/smoke/install-and-run.sh
