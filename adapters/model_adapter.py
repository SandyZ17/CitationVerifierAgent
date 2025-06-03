from abc import ABC, abstractmethod


class BaseModelAdapter(ABC):
    @abstractmethod
    def verify_citation(self, citation_text, paper_content):
        """
        核查引文与文献内容的对应关系
        :param citation_text: 文档中的引文文本
        :param paper_content: 下载的文献内容（如摘要、正文）
        :return: 核查结果（是否匹配及具体分析）
        """
        pass
