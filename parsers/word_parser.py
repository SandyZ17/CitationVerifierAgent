import re
from docx import Document
from utils.refer_parser import parse_ieee_reference
from parsers.file_parser import FileParser, register_doc_parser


@register_doc_parser("docx")
class WordParser(FileParser):
    """
    Word解析器
    """
    @staticmethod
    def extract_references(doc_path):
        """
        提取Word文档中的参考文献部分
        :param doc_path: Word文档路径
        :return: 参考文献列表
        """
        doc = Document(doc_path)
        references = []
        in_references_section = False

        for para in doc.paragraphs:
            text = para.text.strip()

            # 1. 起始判断：是否进入“参考文献”区域
            if not in_references_section:
                # 如果标题为参考文献则开始提取
                if text == "参考文献" or text == "References":
                    in_references_section = True
                continue

            parse_res = parse_ieee_reference(text)
            if not parse_res:
                continue
            else:
                references.append(parse_res)

        return references
