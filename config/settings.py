# src/config/settings.py
import os
from dotenv import load_dotenv


load_dotenv()

# arXiv配置
ARXIV_API_URL = "http://export.arxiv.org/api/query"
DEFAULT_MAX_RESULTS = 10

# 大模型配置
MODEL_CONFIGS = {
    "openai": {
        "api_key": os.getenv("API_KEY"),
        "endpoint": "https://api.openai.com/v1/chat/completions",
        "model": os.getenv("LLM_MODEL", "gpt-3.5-turbo")
    },
    "dashscope": {
        "api_key": os.getenv("API_KEY"),
        "endpoint": "https://api.dashscope.com/api/v1/services/text-generation/v1",
        "model": os.getenv("LLM_MODEL", "qwen-max")
    },
    "anthropic": {
        "api_key": os.getenv("API_KEY"),
        "endpoint": "https://api.anthropic.com/v1/complete",
        "model": os.getenv("LLM_MODEL", "claude-2")
    }
}
