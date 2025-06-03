import requests
import openai
from adapters.model_adapter import BaseModelAdapter
from config.settings import MODEL_CONFIGS


class OpenAIAdapter(BaseModelAdapter):
    def __init__(self):
        self.config = MODEL_CONFIGS["openai"]
        self.headers = {
            "Authorization": f"Bearer {self.config['api_key']}",
            "Content-Type": "application/json"
        }

    def verify_citation(self, citation_text, paper_content):
        prompt = f"请核查以下引文是否与文献内容匹配：\n引文：{citation_text}\n文献内容：{paper_content}\n请输出匹配程度(高/中/低)及简要分析。"
        payload = {
            "model": self.config["model"],
            "messages": [{"role": "user", "content": prompt}]
        }
        try:
            response = requests.post(
                self.config["endpoint"], json=payload, headers=self.headers)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"OpenAI核查失败: {str(e)}")
            return "核查失败"
