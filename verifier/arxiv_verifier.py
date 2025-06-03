import os
import fitz
from parsers.latex_parser import LatexParser
from parsers.word_parser import WordParser
from clients.arxiv_client import ArxivClient
from adapters.adapter_factory import ModelAdapterFactory


class CitationVerificationSystem:
    def __init__(self, download_dir="downloads"):
        self.parser = None
        self.arxiv_client = ArxivClient()
        self.model_adapter = ModelAdapterFactory().get_adapter("dashscope")
        self.download_dir = download_dir
        os.makedirs(self.download_dir, exist_ok=True)

    def set_parser(self, file_ext):
        parser_map = {
            ".tex": LatexParser,
            ".docx": WordParser,
        }
        parser_cls = parser_map.get(file_ext.lower())
        if not parser_cls:
            raise ValueError(f"不支持的文档类型: {file_ext}")
        self.parser = parser_cls()

    def extract_pdf_summary(self, pdf_path):
        try:
            doc = fitz.open(pdf_path)
            selected_pages = []

            if doc.page_count >= 1:
                selected_pages.append(doc.load_page(0).get_text())  # Abstract
            if doc.page_count >= 2:
                selected_pages.append(doc.load_page(1).get_text())  # Metadata
            if doc.page_count >= 3:
                selected_pages.append(
                    doc.load_page(-2).get_text())  # References
            if doc.page_count >= 4:
                selected_pages.append(
                    doc.load_page(-1).get_text())  # References

            doc.close()
            return "\n".join(selected_pages)
        except Exception as e:
            print(f"[错误] 无法读取 PDF 文件: {pdf_path}, 错误: {e}")
            return ""

    def download_if_needed(self, arxiv_id):
        pdf_path = os.path.join(self.download_dir, f"{arxiv_id}.pdf")
        if os.path.exists(pdf_path):
            print(f"[跳过] 文件已存在: {pdf_path}")
            return pdf_path

        print(f"[下载] 正在下载: {arxiv_id} → {pdf_path}")
        success = self.arxiv_client.download_pdf(arxiv_id, pdf_path)
        if success:
            return pdf_path
        else:
            print(f"[失败] 下载失败: {arxiv_id}")
            return None

    def verify_citations(self, doc_path):
        if not os.path.isfile(doc_path):
            raise FileNotFoundError(f"找不到文件: {doc_path}")

        _, ext = os.path.splitext(doc_path)
        self.set_parser(ext)

        references = self.parser.extract_references(doc_path)
        if not references:
            print("⚠️ 未提取到参考文献")
            return

        for ref in references:
            arxiv_id = ref.get("arxiv_id")
            if not arxiv_id:
                print(f"[跳过] 缺失 arXiv ID: {ref.get('title')}")
                continue

            pdf_path = self.download_if_needed(arxiv_id)
            if not pdf_path:
                continue

            pdf_text = self.extract_pdf_summary(pdf_path)
            print(f"[内容预览] {arxiv_id} 前200字符:\n{pdf_text[:200]}...\n")

            # ⚠️ 打开注释以启用模型核查
            # result = self.model_adapter.verify_citation(ref["text"], pdf_text)
            # print(f"[核查结果] {arxiv_id}: {result}")


if __name__ == "__main__":
    system = CitationVerificationSystem()
    system.verify_citations("example.tex")
    # system.verify_citations("example.docx")
