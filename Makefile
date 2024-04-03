# use `make help` to list all targets documented with trailing ## comments
# taken from https://marmelab.com/blog/2016/02/29/auto-documented-makefile.html
.DEFAULT_GOAL := help
.PHONY: help
help: ## show this help message with common targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	sort | \
	awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'


# create python virtual environment for dependency management
VENV_DIR := .venv
VENV_TARGET := $(VENV_DIR)/pyvenv.cfg
VENV_BIN := $(VENV_DIR)/bin
.PHONY: venv
venv: $(VENV_TARGET) ## create a new python virtual environment
	@echo Use \`source $(VENV_DIR)/bin/activate\` to activate the virtual environment
$(VENV_TARGET):
	python3 -m venv $(VENV_DIR)
PYTHON_CMD := $(VENV_BIN)/python3


# hatch environment for development
HATCH_BIN := $(VENV_BIN)/hatch
HATCH_CMD := $(PYTHON_CMD) -m hatch run python
$(HATCH_BIN): $(VENV_TARGET)
	$(PYTHON_CMD) -m pip install hatch


# test suites
.PHONY: test test-examples test-unit
test: test-examples test-unit ## run all test suites
ALL_EXAMPLES := $(wildcard docs/examples/*.py)
test-examples: $(ALL_EXAMPLES) ## run example code test suite
.PHONY: $(ALL_EXAMPLES)
$(ALL_EXAMPLES): $(HATCH_BIN)
	$(HATCH_CMD) $@
test-unit: $(VENV_TARGET) ## run unit test suite
	$(HATCH_CMD) -m unittest discover -s tests
