from abc import abstractmethod


class FileParser:

    _registry = {}

    @classmethod
    def create(cls, doc_type, **kwargs):
        if doc_type not in cls._registry:
            raise ValueError(f"未知文件类型: {doc_type}")
        return cls._registry[doc_type](**kwargs)

    @abstractmethod
    def extract_references(self, doc_path):
        """
        提取文件中的参考文献部分
        :param doc_path: 文件路径
        :return: 参考文献列表
        """
        raise NotImplementedError()

    @abstractmethod
    def extract_abstract(self, doc_path):
        """
        提取文件中的摘要部分
        :param doc_path: 文件路径
        :return: 摘要文本
        """
        raise NotImplementedError()


def register_doc_parser(model_type):
    def decorator(cls):
        FileParser._registry[model_type] = cls
        return cls
    return decorator
