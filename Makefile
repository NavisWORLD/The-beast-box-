PYTHON ?= python
ACCEPTANCE_OUTPUT ?= build/architecture-acceptance.json

.PHONY: install cosmic smoke demo quality env-check lint typecheck test acceptance security sealed-evidence package-smoke

install:
	$(PYTHON) -m pip install -e .

cosmic:
	$(PYTHON) -m beastbox.cosmic_entry

smoke:
	$(PYTHON) -m beastbox.cosmic_entry --smoke

demo:
	$(PYTHON) -m beastbox.cosmic_entry --demo --data-dir ./beast-demo

quality: env-check lint typecheck test acceptance security sealed-evidence

env-check:
	$(PYTHON) -m beastbox.env_inventory --check .env.example beastbox

lint:
	$(PYTHON) -m ruff check scripts/benchmark_runtime.py scripts/smoke/html_browser.py html/serve.py \
		tests/test_runtime_benchmark.py tests/test_runtime_performance.py tests/test_html_server.py
	$(PYTHON) -m ruff check beastbox/env_inventory.py tests/test_env_inventory.py
	$(PYTHON) -m ruff check beastbox/doctor.py beastbox/portable_state.py tests/test_launch_surface.py tests/test_compatible_provider.py
	$(PYTHON) -m ruff check beastbox/cosmic_demo.py tests/test_cosmic_product_polish.py scripts/smoke/cosmic_browser.py
	$(PYTHON) -m ruff check beastbox/aliases.py beastbox/hashutil.py beastbox/logging_config.py \
		beastbox/continuity.py beastbox/durable.py beastbox/events.py beastbox/providers.py \
		beastbox/runtime_cli.py beastbox/swap_receipt.py scripts/run_architecture_acceptance.py \
		scripts/productization_receipt.py tests/test_durable_runtime.py tests/test_product_spine.py \
		tests/test_runtime_cli.py tests/test_swap_receipt.py tests/test_experimental_boundary.py \
		scripts/seal_release_verification.py tests/test_release_verification.py \
		beastbox/desktop.py beastbox/optional_resources.py beastbox/sensor_inputs.py tests/test_runtime_exchange.py \
		beastbox/product_services.py tests/test_product_services.py tests/test_product_observability.py beastbox/memory.py \
		beastbox/cosmic_web.py beastbox/cosmic_ui.py beastbox/cosmic_entry.py tests/test_cosmic_web.py tests/test_cosmic_completion.py tests/test_cosmic_closure.py \
		beastbox/sealed_storage.py beastbox/profiles.py tests/test_sealed_storage.py tests/test_profile_isolation.py tests/test_product_acceptance.py tests/test_mobile_release_contract.py
	$(PYTHON) -m ruff check beastbox/training scripts/freeze_zeref_genesis.py scripts/build_lexical_corpus.py \
		scripts/build_world_corpus.py tests/test_training_lineage.py tests/test_training_corpus.py

typecheck:
	$(PYTHON) -m mypy beastbox/env_inventory.py beastbox/logging_config.py beastbox/hashutil.py beastbox/aliases.py \
		beastbox/continuity.py beastbox/durable.py beastbox/events.py beastbox/providers.py \
		beastbox/cli.py beastbox/cypher/models.py beastbox/runtime_cli.py beastbox/swap_receipt.py \
		beastbox/product_services.py beastbox/memory.py beastbox/cosmic_web.py beastbox/cosmic_ui.py beastbox/cosmic_entry.py \
		beastbox/sealed_storage.py beastbox/profiles.py beastbox/training/lineage.py beastbox/training/corpus.py \
		scripts/run_architecture_acceptance.py beastbox/cosmic_demo.py

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
