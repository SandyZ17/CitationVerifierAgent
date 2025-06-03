# src/parsers/word_parser.py
from docx import Document
import re
from utils.refer_parser import parse_ieee_reference


class WordParser:
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


if __name__ == "__main__":
    # 测试示例
    parser = WordParser()
    refs = parser.extract_references("test.docx")
    print("提取到的参考文献：", refs)
