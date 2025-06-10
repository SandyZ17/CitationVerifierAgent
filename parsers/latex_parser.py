import re
from parsers.file_parser import FileParser, register_doc_parser


@register_doc_parser("tex")
class LatexParser(FileParser):
    """
    LatexParser类用于解析LaTeX文档中的参考文献部分
    """
    @staticmethod
    def extract_references(tex_path):
        """
        提取LaTeX文档中的参考文献部分
        :param tex_path: LaTeX文档路径
        :return: 参考文献列表
        """
        with open(tex_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 匹配thebibliography环境内容
        bib_pattern = re.compile(
            r'\\begin{thebibliography}{.*?}(.*?)\\end{thebibliography}', re.DOTALL)
        match = bib_pattern.search(content)
        references = []

        if match:
            bib_content = match.group(1)
            # 提取每个\bibitem条目
            item_pattern = re.compile(
                r'\\bibitem{(.*?)}(.*?)(?=\\bibitem|\\end{thebibliography})', re.DOTALL)
            for item in item_pattern.findall(bib_content):
                ref = item[1].strip().replace('\\n', ' ').replace('  ', ' ')
                references.append(ref)

        # 若未找到thebibliography，尝试提取bibtex引用键（需配合.bib文件使用）
        if not references:
            cite_pattern = re.compile(r'\\cite{([^}]+)}')
            cite_keys = cite_pattern.findall(content)
            references = [key.strip() for key in ','.join(
                cite_keys).split(',') if key.strip()]

        return references
