"""Configuration settings for E-commerce AI system.

AI Provider Setup:

Ollama (Local - Recommended):
  1. Install: https://ollama.ai
  2. Pull a model: ollama pull llama2  (or mistral, neural-chat, etc.)
  3. Run: ollama serve
  4. Demo will connect automatically

OpenAI (Cloud):
  1. Set AI_PROVIDER = "openai"
  2. Set AI_MODEL = "qwen2.5-coder:1.5b")
  3. Export: export OPENAI_API_KEY="sk-..."
  4. Run demo

Anthropic (Cloud):
  1. Set AI_PROVIDER = "anthropic"
  2. Set AI_MODEL = "qwen2.5-coder:1.5b"
  3. Export: export ANTHROPIC_API_KEY="sk-ant-..."
  4. Run demo
"""

from pathlib import Path

# Database
DATABASE_PATH = Path(__file__).parent.parent.parent / "data" / "ecommerce.db"
DATABASE_TYPE = "sqlite"

# AI Settings
# Choose provider: "ollama" (local), "openai" (cloud), "anthropic" (cloud)
AI_PROVIDER = "ollama"
# For Ollama models, ranked by SQL generation quality:
# 1. "phind-codellama:34b" (best for SQL, fine-tuned for code, needs ~20GB RAM)
# 2. "codellama:13b-instruct" (good balance, code-specific)
# 3. "mixtral:8x7b" (excellent reasoning, needs ~26GB RAM)
# 4. "mistral" (fast, decent quality)
# For OpenAI: try "gpt-4", "gpt-3.5-turbo"
# For Anthropic: try "claude-3-opus", "claude-3-sonnet"
AI_MODEL = "qwen2.5-coder:1.5b"  # Recommended: best SQL generation quality
AI_TEMPERATURE = 0.7
AI_MAX_TOKENS = 500

# Query Agent Settings
ENABLE_PLANNING = True
ENABLE_INSIGHTS = True
MAX_RETRIES = 2

# Logging
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
