.PHONY: help venv install test coverage lint typecheck security clean clean-all build mcp-example review rag-install rag-ingest rag-query rag-chat rag-stats rag-api precommit-install ci-local 1 2 3

# Virtual environment name (can be overridden)
# Usage: make venv [name] or make venv env_name=name
# If a second argument is provided, use it as env_name
ifneq ($(word 2,$(MAKECMDGOALS)),)
env_name := $(word 2,$(MAKECMDGOALS))
# Make the second argument a phony no-op target so it always runs
.PHONY: $(word 2,$(MAKECMDGOALS))
$(eval $(word 2,$(MAKECMDGOALS)):;@:)
else
env_name ?= venv
endif

# Detect which virtual environment exists and use it
# Priority: 1) Currently activated venv (VIRTUAL_ENV), 2) env_name, 3) common names, 4) scan all
VENV_DETECT := $(shell \
	if [ -n "$$VIRTUAL_ENV" ]; then \
		basename "$$VIRTUAL_ENV"; \
	elif [ -d "$(env_name)" ] && [ -f "$(env_name)/bin/activate" ]; then \
		echo "$(env_name)"; \
	elif [ -d "venv" ] && [ -f "venv/bin/activate" ]; then \
		echo "venv"; \
	elif [ -d ".ci-venv" ] && [ -f ".ci-venv/bin/activate" ]; then \
		echo ".ci-venv"; \
	elif [ -d "server" ] && [ -f "server/bin/activate" ]; then \
		echo "server"; \
	elif [ -d "logger" ] && [ -f "logger/bin/activate" ]; then \
		echo "logger"; \
	else \
		for dir in */bin/activate; do \
			if [ -f "$$dir" ]; then \
				dirname "$$dir" | sed 's|/bin||'; \
				break; \
			fi; \
		done; \
	fi)

# Python for targets without an activated venv (must be >= 3.12 on PATH).
PYTHON := $(if $(VENV_DETECT),./$(VENV_DETECT)/bin/python,python3.12)

help:
	@echo "axiompy - Makefile commands"
	@echo ""
	@echo "  make venv [name]             - Create venv with Python >= 3.12 (default: venv)"
	@echo "      VENV_PYTHON=/path/to/python3.12  - if python3.12 is not on PATH"
	@echo "  make install [env_name=name] - Install package in dev mode to venv"
	@echo "  make test [env_name=name]    - Run tests using venv"
	@echo "  make coverage [env_name=name]- Run tests with coverage using venv"
	@echo "  make lint                    - Run ruff and pylint"
	@echo "  make typecheck               - Run mypy type checker"
	@echo "  make security                - Run bandit and pip-audit"
	@echo "  make ci-local                - Run Ruff, pre-commit, tests+coverage, security (matches CI)"
	@echo "  make clean                   - Clean build artifacts"
	@echo "  make clean-all [name]        - Clean and remove venv (default: venv)"
	@echo "  make build                   - Build distribution package (poetry build)"
	@echo "  make precommit-install       - (Re)install git hooks via pre-commit"
	@echo ""
	@echo "  Note: 'make venv' and 'make install' auto-install the pre-commit hooks."
	@echo ""
	@echo "Code Review (requires axiompy-agents in the environment):"
	@echo "  make review FILE=/path/to/file.py  - Review a single file"
	@echo ""
	@echo "RAG Agent (requires axiompy-agents in the environment):"
	@echo "  make rag-install                   - Install all RAG dependencies"
	@echo "  make rag-ingest PATHS='./docs/'    - Ingest documents"
	@echo "  make rag-query Q='What is X?'      - Query the RAG system"
	@echo "  make rag-chat                      - Interactive chat mode"
	@echo "  make rag-stats                     - Show index statistics"
	@echo "  make rag-api                       - Start RAG REST API server"
	@echo "  Options: EMBEDDER=fastembed MODEL=mistral SOURCES=1 VERBOSE=1"
	@echo "  Persistence: STORE=chroma PERSIST_PATH=./rag_data"
	@echo ""
	@echo "AI Demo Examples:"
	@echo "  make mcp-example                              # Use default (qwen2.5-coder:1.5b)"
	@echo "  make mcp-example MODEL=qwen2.5-coder:1.5b     # Fastest, smallest (~1GB) [RECOMMENDED]"
	@echo "  make mcp-example MODEL=deepseek-coder:1.3b    # Fast & efficient (~1GB)"
	@echo "  make mcp-example MODEL=mistral                # Reliable all-rounder (~4GB)"
	@echo "  make mcp-example MODEL=codellama:7b           # Code specialist (~4GB)"
	@echo "  make mcp-interactive                          # Run interactive demo"
	@echo ""
	@echo "Examples / Demos:"
	@echo "  make mcp-example              - Setup and run E-Commerce AI demo (all-in-one)"
	@echo ""
	@echo "Examples:"
	@echo "  make venv                    - Creates 'venv' directory"
	@echo "  make venv server             - Creates 'server' directory"
	@echo "  make test                    - Run tests with auto-detected venv"
	@echo "  make test env_name=server    - Run tests with 'server' venv"
	@echo ""
	@echo "Note: test/install/coverage auto-detect venv in this order:"
	@echo "      1) Currently activated venv (VIRTUAL_ENV)"
	@echo "      2) env_name parameter > venv > .ci-venv > server > logger"
	@echo "      3) Any directory with bin/activate"

# Code Review (requires axiompy-agents installed in the active venv)
review:
	@if [ -z "$(FILE)" ]; then \
		echo "Usage: make review FILE=/path/to/file.py"; \
		exit 1; \
	fi
	@$(PYTHON) -c "import axiompy.agents" 2>/dev/null || ( \
		echo >&2 "This target needs axiompy-agents. Clone the axiompy-agents repo and: pip install -e \".[test-all]\""; \
		exit 1 \
	)
	@echo "Reviewing $(FILE)..."
	@$(PYTHON) -c "import time; from axiompy.agents.code_review import CodeReviewServiceFactory; start=time.time(); svc=CodeReviewServiceFactory.create_for_filesystem(rules_path='AGENTS.md', show_progress=True); r=svc.review_files(['$(FILE)'], mode='$(or $(MODE),standard)'); print(f'Time: {time.time()-start:.1f}s | Score: {r.score}/100 | Violations: {r.violation_count}')"

# RAG Agent
# Common options: EMBEDDER=fastembed|sentence_transformers STORE=memory|chroma PERSIST_PATH=./rag_data

rag-install:
	@if [ -z "$(VENV_DETECT)" ]; then \
		echo "Error: No virtual environment found. Run 'make venv' first."; \
		exit 1; \
	fi
	@if ./$(VENV_DETECT)/bin/python -c "import axiompy.agents" 2>/dev/null; then \
		echo "axiompy-agents already importable; upgrading optional RAG stack..."; \
	else \
		if [ -d "../axiompy-agents" ]; then \
			echo "Installing sibling ../axiompy-agents[rag,test-all] into $(VENV_DETECT)..."; \
			./$(VENV_DETECT)/bin/pip install -e "../axiompy-agents[rag,test-all]"; \
		else \
			echo >&2 "Clone the axiompy-agents repository next to this repo, then re-run make rag-install"; \
			echo >&2 "Or: pip install \"axiompy-agents[rag,test-all]\""; \
			exit 1; \
		fi; \
	fi
	@echo "Installing RAG dependencies to: $(VENV_DETECT)"
	@echo ""
	@echo "Installing embedders..."
	@./$(VENV_DETECT)/bin/pip install -q fastembed
	@./$(VENV_DETECT)/bin/pip install -q sentence-transformers 'transformers<4.50'
	@echo "✓ Embedders installed (fastembed, sentence-transformers)"
	@echo ""
	@echo "Installing vector stores..."
	@./$(VENV_DETECT)/bin/pip install -q chromadb
	@./$(VENV_DETECT)/bin/pip install -q 'numpy>=1.24.0,<2.0'
	@echo "✓ Vector stores installed (chromadb, numpy)"
	@echo ""
	@echo "Installing document sources..."
	@./$(VENV_DETECT)/bin/pip install -q pypdf
	@echo "✓ Document sources installed (pypdf)"
	@echo ""
	@echo "═══════════════════════════════════════════════════════════════"
	@echo "✓ RAG dependencies installed successfully!"
	@echo ""
	@echo "Available embedders:  fastembed, sentence_transformers, ollama, openai"
	@echo "Available stores:     memory, chroma, pinecone, pgvector"
	@echo "Available sources:    filesystem, url, object_store, database, pdf"
	@echo ""
	@echo "Quick start:"
	@echo "  make rag-ingest PATHS='./docs/' EMBEDDER=fastembed"
	@echo "  make rag-query Q='What is X?'"
	@echo "═══════════════════════════════════════════════════════════════"

rag-ingest:
	@if [ -z "$(PATHS)" ]; then \
		echo "Usage: make rag-ingest PATHS='./docs/'"; \
		echo "Options: STORE=chroma PERSIST_PATH=./rag_data EMBEDDER=fastembed VERBOSE=1"; \
		exit 1; \
	fi
	@$(PYTHON) -c "import axiompy.agents" 2>/dev/null || (echo >&2 "Install axiompy-agents first (see make rag-install)."; exit 1)
	@$(PYTHON) -m axiompy.agents.rag.applications.cli ingest $(PATHS) \
		$(if $(EMBEDDER),--embedder $(EMBEDDER),) \
		$(if $(STORE),--store $(STORE),) \
		$(if $(PERSIST_PATH),--persist-path $(PERSIST_PATH),) \
		$(if $(VERBOSE),-v,)

rag-query:
	@if [ -z "$(Q)" ]; then \
		echo "Usage: make rag-query Q='What is X?'"; \
		echo "Options: STORE=chroma PERSIST_PATH=./rag_data EMBEDDER=fastembed SOURCES=1"; \
		exit 1; \
	fi
	@$(PYTHON) -c "import axiompy.agents" 2>/dev/null || (echo >&2 "Install axiompy-agents first (see make rag-install)."; exit 1)
	@$(PYTHON) -m axiompy.agents.rag.applications.cli query "$(Q)" \
		$(if $(EMBEDDER),--embedder $(EMBEDDER),) \
		$(if $(STORE),--store $(STORE),) \
		$(if $(PERSIST_PATH),--persist-path $(PERSIST_PATH),) \
		$(if $(SOURCES),--show-sources,) \
		$(if $(VERBOSE),-v,)

rag-chat:
	@$(PYTHON) -c "import axiompy.agents" 2>/dev/null || (echo >&2 "Install axiompy-agents first (see make rag-install)."; exit 1)
	@$(PYTHON) -m axiompy.agents.rag.applications.cli chat \
		$(if $(EMBEDDER),--embedder $(EMBEDDER),) \
		$(if $(STORE),--store $(STORE),) \
		$(if $(PERSIST_PATH),--persist-path $(PERSIST_PATH),) \
		$(if $(MODEL),--model $(MODEL),)

rag-stats:
	@$(PYTHON) -c "import axiompy.agents" 2>/dev/null || (echo >&2 "Install axiompy-agents first (see make rag-install)."; exit 1)
	@$(PYTHON) -m axiompy.agents.rag.applications.cli stats \
		$(if $(EMBEDDER),--embedder $(EMBEDDER),) \
		$(if $(STORE),--store $(STORE),) \
		$(if $(PERSIST_PATH),--persist-path $(PERSIST_PATH),)

rag-api:
	@echo "Starting RAG API server..."
	@echo "Options: RAG_STORE=chroma RAG_PERSIST_PATH=./rag_data RAG_PORT=8080"
	@$(PYTHON) -c "import axiompy.agents" 2>/dev/null || (echo >&2 "Install axiompy-agents first (see make rag-install)."; exit 1)
	@$(PYTHON) -m axiompy.agents.rag.applications.api

venv:
	@PY=$$("$(CURDIR)/scripts/resolve_python312.sh"); \
	echo "Using $$PY for virtualenv ($$($$PY -V))..."; \
	if [ -d "$(env_name)" ]; then \
		echo "Virtual environment '$(env_name)' already exists, updating..."; \
	else \
		echo "Creating virtual environment: $(env_name)..."; \
		$$PY -m venv $(env_name); \
		echo "Virtual environment created!"; \
	fi
	@echo "Upgrading pip..."
	@./$(env_name)/bin/pip install --upgrade pip
	@echo "Installing dependencies from requirements-dev.txt..."
	@./$(env_name)/bin/pip install -r requirements-dev.txt
	@echo "Installing editable axiompy (core only)..."
	@./$(env_name)/bin/pip install -e ".[dev,servers,databases,storage,http,http-async]"
	@$(MAKE) precommit-install env_name=$(env_name)
	@echo ""
	@echo "✓ Virtual environment setup complete!"
	@echo "To activate: source $(env_name)/bin/activate"

install:
	@if [ -z "$(VENV_DETECT)" ]; then \
		echo "Error: No virtual environment found. Run 'make venv' first."; \
		exit 1; \
	fi
	@echo "Installing to virtual environment: $(VENV_DETECT)..."
	@./$(VENV_DETECT)/bin/pip install -r requirements-dev.txt
	@./$(VENV_DETECT)/bin/pip install -e ".[dev,servers,databases,storage,http,http-async]"
	@$(MAKE) precommit-install env_name=$(VENV_DETECT)
	@echo "✓ Installation complete!"

# Install pre-commit git hooks. Idempotent; safe to call repeatedly.
# Skips silently if not inside a git checkout (e.g. tarball install).
.PHONY: precommit-install
precommit-install:
	@VENV_PATH=$${env_name:-$(VENV_DETECT)}; \
	if [ ! -d ".git" ]; then \
		echo "Not a git checkout — skipping pre-commit install"; \
		exit 0; \
	fi; \
	if [ ! -x "./$$VENV_PATH/bin/pre-commit" ]; then \
		echo "pre-commit not installed in $$VENV_PATH — skipping hook install"; \
		echo "  (run 'pip install pre-commit' to enable)"; \
		exit 0; \
	fi; \
	echo "Installing git hooks via pre-commit..."; \
	./$$VENV_PATH/bin/pre-commit install --install-hooks || exit 1; \
	./$$VENV_PATH/bin/pre-commit install --hook-type pre-push || exit 1; \
	echo "✓ Git hooks installed (commit + pre-push)"

test:
	@if [ -z "$(VENV_DETECT)" ]; then \
		echo "Error: No virtual environment found. Run 'make venv' first."; \
		exit 1; \
	fi
	@echo "Running tests with: $(VENV_DETECT)"
	$(PYTHON) -m pytest tests

coverage:
	@if [ -z "$(VENV_DETECT)" ]; then \
		echo "Error: No virtual environment found. Run 'make venv' first."; \
		exit 1; \
	fi
	@echo "Running coverage with: $(VENV_DETECT)"
	$(PYTHON) -m pytest tests --cov=axiompy --cov-report=html --cov-report=term

lint:
	@echo "Running linters..."
	ruff check . --fix
	ruff format .
	pylint axiompy/ --rcfile=pyproject.toml --fail-under=10.0

typecheck:
	@echo "Running type checker..."
	mypy axiompy/ --ignore-missing-imports

security:
	@echo "Running security scans..."
	bandit -c pyproject.toml -r axiompy/ -ll
	pip-audit

# Match .github/workflows/python-ci.yml (lint + test + security) and pre-commit run --all-files.
ci-local:
	@if [ -z "$(VENV_DETECT)" ]; then \
		echo >&2 "No venv found. Run: make venv   then: source venv/bin/activate"; \
		exit 1; \
	fi
	@set -e; VP=./$(VENV_DETECT)/bin; \
	echo "Using venv: $(VENV_DETECT)"; \
	echo ""; echo "== 1/4 Ruff (CI lint job) =="; \
	$$VP/ruff check . --config pyproject.toml; \
	$$VP/ruff format --check . --config pyproject.toml; \
	echo ""; echo "== 2/4 Pre-commit (all hooks, all files) =="; \
	$$VP/pre-commit run --all-files; \
	echo ""; echo "== 3/4 Pytest + coverage (CI test job) =="; \
	$$VP/pytest tests/ --cov=axiompy --cov-report=xml --cov-report=term; \
	$$VP/coverage report --fail-under=80; \
	echo ""; echo "== 4/4 Bandit + pip-audit (CI security job) =="; \
	$$VP/bandit -c pyproject.toml -r axiompy/ -ll; \
	$$VP/pip-audit; \
	echo ""; echo "✓ ci-local: all checks passed (matches GitHub Actions)."

clean:
	rm -rf build/ dist/ *.egg-info .pytest_cache/ .coverage htmlcov/
	rm -rf axiompy/*.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

clean-all: clean
	@echo "Removing virtual environment: $(env_name)..."
	rm -rf $(env_name)/
	rm -rf .ruff_cache/

build: clean
	poetry build

mcp-example: ## AI Demo: make mcp-example [1|2|3] - 1=qwen2.5-coder:1.5b, 2=deepseek-coder:1.3b, 3=mistral
	@# Parse model selection (1, 2, or 3)
	$(eval OPTION := $(filter 1 2 3,$(MAKECMDGOALS)))
	$(eval MODEL := $(if $(filter 1,$(OPTION)),qwen2.5-coder:1.5b,$(if $(filter 2,$(OPTION)),deepseek-coder:1.3b,$(if $(filter 3,$(OPTION)),mistral,qwen2.5-coder:1.5b))))
	@echo "════════════════════════════════════════════════════════════════════════════════"
	@echo "  AxiomPy Reasoning Module - E-commerce AI Demo"
	@echo "════════════════════════════════════════════════════════════════════════════════"
	@echo ""
	@echo "Model Options:"
	@echo "  1. qwen2.5-coder:1.5b (fastest, most reliable, ~1GB RAM) $(if $(filter 1,$(OPTION)),← SELECTED,)"
	@echo "  2. deepseek-coder:1.3b (fast & efficient, ~1GB RAM) $(if $(filter 2,$(OPTION)),← SELECTED,)"
	@echo "  3. mistral (reliable all-rounder, ~4GB RAM) $(if $(filter 3,$(OPTION)),← SELECTED,)"
	@echo ""
	@echo "Selected: $(MODEL) $(if $(OPTION),,← DEFAULT)"
	@echo "════════════════════════════════════════════════════════════════════════════════"
	@echo ""
	@if [ -z "$(VENV_DETECT)" ]; then \
		echo "Step 1: Creating virtual environment..."; \
		PY=$$("$(CURDIR)/scripts/resolve_python312.sh"); \
		$$PY -m venv venv; \
		VENV_PATH=venv; \
		echo "✓ Virtual environment created"; \
	else \
		echo "Step 1: Using existing virtual environment: $(VENV_DETECT)"; \
		VENV_PATH=$(VENV_DETECT); \
	fi
	@VENV_PATH=$${VENV_PATH:-$(VENV_DETECT)}; \
	echo ""; \
	echo "Step 2: Installing Ollama (required for AI features)..."; \
	if command -v ollama &> /dev/null; then \
		echo "✓ Ollama is already installed"; \
	else \
		echo "Installing Ollama..."; \
		if [ "$$(uname)" = "Darwin" ]; then \
			if command -v brew &> /dev/null; then \
				echo "  Installing via Homebrew..."; \
				brew install ollama; \
				if [ $$? -ne 0 ]; then \
					echo ""; \
					echo "❌ Failed to install Ollama via brew."; \
					echo ""; \
					echo "Please install manually from: https://ollama.ai"; \
					exit 1; \
				fi; \
			else \
				echo ""; \
				echo "❌ Homebrew not found. Cannot auto-install Ollama."; \
				echo ""; \
				echo "Please install Ollama manually from: https://ollama.ai"; \
				exit 1; \
			fi; \
		elif [ "$$(uname)" = "Linux" ]; then \
			echo ""; \
			echo "❌ Please install Ollama from: https://ollama.ai"; \
			echo ""; \
			echo "On Linux, you can run:"; \
			echo "  curl https://ollama.ai/install.sh | sh"; \
			exit 1; \
		else \
			echo ""; \
			echo "❌ Unsupported OS. Please install Ollama from: https://ollama.ai"; \
			exit 1; \
		fi; \
	fi
	@echo ""
	@echo "Step 3: Checking Ollama service..."
	@bash scripts/check_ollama.sh
	@echo ""
	@echo "Step 4: Pulling Ollama model ($(MODEL))..."
	@if ! ollama list | grep -qF "$(MODEL)"; then \
		echo "  Downloading $(MODEL) model (this may take several minutes)..."; \
		ollama pull "$(MODEL)"; \
		if [ $$? -ne 0 ]; then \
			echo ""; \
			echo "❌ Failed to pull $(MODEL) model."; \
			echo ""; \
			echo "Try manually:"; \
			echo "  ollama pull $(MODEL)"; \
			exit 1; \
		fi; \
		echo "✓ $(MODEL) model downloaded"; \
	else \
		echo "✓ $(MODEL) model is already available"; \
	fi
	@VENV_PATH=$${VENV_PATH:-$(VENV_DETECT)}; \
	echo ""; \
	echo "Step 5: Installing Python dependencies..."; \
	$$VENV_PATH/bin/pip install -q --upgrade pip; \
	$$VENV_PATH/bin/pip install -q -r requirements-dev.txt; \
	$$VENV_PATH/bin/pip install -q -e .; \
	if $$VENV_PATH/bin/python -c "import axiompy.reasoning" 2>/dev/null; then \
		echo "✓ axiompy.reasoning available"; \
	elif [ -d "../axiompy-agents" ]; then \
		echo "Installing sibling axiompy-agents for the reasoning demo..."; \
		$$VENV_PATH/bin/pip install -q -e "../axiompy-agents[test-all]"; \
	else \
		echo >&2 "This demo needs axiompy.reasoning (axiompy-agents). Clone varonusmaximus/axiompy-agents next to this repo or: pip install axiompy-agents"; \
		exit 1; \
	fi; \
	echo "✓ Python dependencies installed"
	@VENV_PATH=$${VENV_PATH:-$(VENV_DETECT)}; \
	if [ ! -f "examples/ecommerce_ai/data/ecommerce.db" ]; then \
		echo ""; \
		echo "Step 6: Generating dataset (1M records - this may take 2-5 minutes)..."; \
		cd examples/ecommerce_ai && ../../$$VENV_PATH/bin/python setup.py; \
		echo "✓ Dataset generated"; \
	else \
		echo ""; \
		echo "Step 6: Dataset already exists (skipping generation)"; \
	fi
	@VENV_PATH=$${VENV_PATH:-$(VENV_DETECT)}; \
	echo ""; \
	echo "Step 7: Updating model configuration..."; \
	sed -i '' 's/AI_MODEL = ".*"/AI_MODEL = "$(MODEL)"/' examples/ecommerce_ai/ecommerce/config/settings.py; \
	echo "✓ Set AI_MODEL = \"$(MODEL)\""; \
	echo ""; \
	echo "Step 8: Running test queries to verify setup..."; \
	echo "=================================================="; \
	echo ""; \
	$$VENV_PATH/bin/python examples/ecommerce_ai/test_query.py
	@echo ""
	@echo "=================================================="; \
	echo "✓ Setup complete!"; \
	echo ""; \
	echo "Current model: $(MODEL)"; \
	echo ""; \
	echo "To run the interactive demo:"; \
	echo "  source venv/bin/activate"; \
	echo "  python examples/ecommerce_ai/interactive_demo.py"; \
	echo ""; \
	echo "To try a different model:"; \
	echo "  make mcp-example 2                           # deepseek-coder:1.3b"; \
	echo "  make mcp-example 3                           # mistral (larger, more capable)"; \
	echo "  make mcp-example MODEL=codellama:7b          # Code specialist"; \
	echo ""

.PHONY: mcp-interactive
mcp-interactive: ## Run the interactive ecommerce AI demo (requires terminal)
	@VENV_PATH=$${VENV_PATH:-$(VENV_DETECT)}; \
	if [ ! -d "$$VENV_PATH" ]; then \
		echo "❌ Virtual environment not found. Run 'make mcp-example' first."; \
		exit 1; \
	fi
	@VENV_PATH=$${VENV_PATH:-$(VENV_DETECT)}; \
	if [ ! -f "examples/ecommerce_ai/data/ecommerce.db" ]; then \
		echo "❌ Dataset not found. Run 'make mcp-example' first."; \
		exit 1; \
	fi
	@VENV_PATH=$${VENV_PATH:-$(VENV_DETECT)}; \
	echo "Launching interactive demo..."; \
	$$VENV_PATH/bin/python examples/ecommerce_ai/interactive_demo.py

# Dummy targets for model selection (1, 2, 3)
1 2 3:
	@:
