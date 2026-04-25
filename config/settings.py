import os
from dotenv import load_dotenv

load_dotenv()

# Anthropic
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# AWS
AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
GITHUB_SECRET_NAME = "agentscope/github-token"

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_USER_ID   = int(os.getenv("TELEGRAM_USER_ID", "0"))

# Models (Anthropic)
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "claude-sonnet-4-6")
FAST_MODEL    = os.getenv("FAST_MODEL",    "claude-haiku-4-5")
SMART_MODEL   = os.getenv("SMART_MODEL",   "claude-opus-4-6")

# Token Limits — tuned per agent role
MAX_TOKENS_ARCHITECT = 8192    # PRD parser + architect (large structured output)
MAX_TOKENS_PLAN      = 4096    # Service-level planning
MAX_TOKENS_CODE      = 8192    # Code generation (full file content)
MAX_TOKENS_REVIEW    = 2048    # Code review (short feedback)
MAX_TOKENS_QA        = 4096    # Test generation
MAX_TOKENS_DOCS      = 8192    # Documentation generation

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_DIR   = "logs"
