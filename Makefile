.DEFAULT_GOAL 	    = help

# try to export environment variables from .env.<stage> file corresponding to the selected stage
env_file ?= .env
ifneq ("$(wildcard $(env_file))","")
include $(env_file)
export $(shell sed 's/=.*//' $(env_file))
endif

define BROWSER_PYSCRIPT
import os, webbrowser, sys
from urllib.request import pathname2url

webbrowser.open("file://" + pathname2url(os.path.abspath(sys.argv[1])))
endef
export BROWSER_PYSCRIPT
BROWSER := python3 -c "$$BROWSER_PYSCRIPT"

.PHONY: help
help: ## this help
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Setup

.PHONY: setup
setup: ## setup dev environment
	uv sync --all-groups
	uv run pre-commit install --install-hooks



##@ Dev

.PHONY: lint
lint: ## run ruff for static code style checks
	uv run ruff check --fix

.PHONY: format
format: ## run ruff for code formatting (will not make any changes inplace)
	uv run ruff format

.PHONY: typing
typing: ## run mypy for static type checks
	uv run mypy

.PHONY: check
check: lint format typing ## run linter, formatter and type checker

.PHONY: unittests
unittests: ## run unittests via pytest
	uv run pytest tests/unittests

.PHONY: integrationtests
integrationtests: ## run integrationtests via pytest
	uv run pytest tests/integrationtests

.PHONY: coverage
coverage: ## run unittests with pytest with coverage and show coverage report in browser
	-uv run coverage run -m pytest tests
	uv run coverage html -i --title "UnboundDB Code Coverage"
	$(BROWSER) htmlcov/index.html

.PHONY: release
release:  ## bump version number to next release
	uv run bump-my-version bump release

.PHONY: dependency-check
dependency-check:  ## run the owasp dependency check on the current workspace
	-mkdir -p odc-report
	-docker run --rm -v "./:/home/atlas" -u $(id -u):$(id -g) --entrypoint="" \
		dockerregistry.mgm-tp.com/com.mgmsp.mgm-atlas/scanners/dependency_check:latest \
		/usr/share/dependency-check/bin/dependency-check.sh \
		--noupdate \
		--scan . \
		--failOnCVSS 7 \
		--format HTML \
		--enableExperimental \
		--disableOssIndex \
		--disableNodeJS \
		--disableAssembly \
		--disableYarnAudit \
		--suppression dependency-check-suppression.xml \
		--out odc-report \
		--project unbounddb
	$(BROWSER) odc-report/dependency-check-report.html



##@ Cleanup

.PHONY: clean
clean: _clean-pypi-build _clean-pyc _clean-coverage _clean-dev-artifacts  ## run cleanup job

.PHONY: _clean-pypi-build
_clean-pypi-build: # remove pypi build artifacts
	-rm -rf build/
	-rm -rf dist/
	-find . -type d -name '*.egg-info' -exec rm -rf {} + 2>/dev/null

.PHONY: _clean-pyc
_clean-pyc: # remove .pyc and .pyo files
	-find . -type f -name "*.py[co]" -delete
	-find . -type d -name "__pycache__" -delete

.PHONY: _clean-dev-artifacts
_clean-dev-artifacts: # clean artifacts from mypy and pytest
	-rm -rf .mypy_cache
	-rm -rf .pytest_cache

.PHONY: _clean-coverage
_clean-coverage: # remove coverage artifacts/ also test cache
	-rm -f .coverage
	-rm -rf htmlcov

