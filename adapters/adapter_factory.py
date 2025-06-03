from adapters.dashscope import DashScopeAdapter
from adapters.openai import OpenAIAdapter


class ModelAdapterFactory:
    @staticmethod
    def get_adapter(model_name):
        if model_name == "openai":
            return OpenAIAdapter()
        elif model_name == "dashscope":
            return DashScopeAdapter()
        else:
            raise ValueError(f"不支持的大模型: {model_name}")
