# src/config/settings.py
import os
from dotenv import load_dotenv
from enum import Enum


class CheckType(Enum):
    CHECK_TYPE_BY_CHAIN = "chain"
    CHECK_TYPE_SIMPLE = "simple"


load_dotenv()

# arXiv配置
ARXIV_API_URL = "http://export.arxiv.org/api/query"
DEFAULT_MAX_RESULTS = 10
CHECK_TYPE = os.getenv("CHECK_TYPE", CheckType.CHECK_TYPE_SIMPLE)

GROBID_URL = os.getenv("GROBID_URL", "http://localhost:8070")

LLM_PLATFORM = os.getenv("LLM_PLATFORM", "dashscope")

# 大模型配置
MODEL_CONFIGS = {
    "openai": {
        "api_key": os.getenv("API_KEY"),
        "endpoint": "https://api.openai.com/v1/chat/completions",
        "model": os.getenv("LLM_MODEL", "gpt-3.5-turbo"),
    },
    "dashscope": {
        "api_key": os.getenv("API_KEY"),
        "endpoint": "https://api.dashscope.com/api/v1/services/text-generation/v1",
        "model": os.getenv("LLM_MODEL", "qwq-plus-2025-03-05"),
        "embedding_model": os.getenv("EMBEDDING_MODEL", "text-embedding-v4"),
    },
    "anthropic": {
        "api_key": os.getenv("API_KEY"),
        "endpoint": "https://api.anthropic.com/v1/complete",
        "model": os.getenv("LLM_MODEL", "claude-2")
    }
}
