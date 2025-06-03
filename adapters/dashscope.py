import dashscope
from adapters.model_adapter import BaseModelAdapter
from config.settings import MODEL_CONFIGS
from adapters.prompt_templates import VERIFY_CITATION_PROMPT


class DashScopeAdapter(BaseModelAdapter):
    def __init__(self):
        self.config = MODEL_CONFIGS["dashscope"]
        self.api_key = self.config["api_key"]
        self.model = self.config["model"]

    def verify_citation(self, citation_text, paper_content):
        prompt = VERIFY_CITATION_PROMPT.format(
            citation_text=citation_text, reference_data=paper_content)
        response = dashscope.Generation.call(
            api_key=self.api_key,
            model=self.model,
            messages=[{
                "role": "user",
                "content": prompt
            }],
            result_format="message"
        )
        return response.output.choices[0].message.content
