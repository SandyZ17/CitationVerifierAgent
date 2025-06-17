import hashlib
import os
import json

from parsers.grobid_parser import GrobidParser
from clients.arxiv_client import ArxivClient
from config.settings import MODEL_CONFIGS

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.llms.tongyi import Tongyi
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.docstore.document import Document
from langchain_core.prompts import PromptTemplate

from utils.academic_paper_splitter import AcademicPaperSplitter


class CitationVerificationSystem:
    def __init__(self, download_dir, doc_path, output_dir):
        if not os.path.isfile(doc_path):
            raise FileNotFoundError(f"找不到文件: {doc_path}")

        self.doc_path = doc_path
        self.doc_id = os.path.splitext(os.path.basename(doc_path))[0]  # 唯一文档ID
        self.parser = GrobidParser(grobid_url="http://localhost:8070")
        self.arxiv_client = ArxivClient()
        self.download_dir = download_dir
        os.makedirs(self.download_dir, exist_ok=True)

        # 向量数据库路径
        self.vector_db_dir = f"faiss_index_{self.doc_id}"
        self.hash_file = f"faiss_hashes_{self.doc_id}.txt"

        self.embeddings = DashScopeEmbeddings(
            model=MODEL_CONFIGS['dashscope']['embedding_model'],
            dashscope_api_key=MODEL_CONFIGS['dashscope']['api_key'])

        self.init_vector_db()
        self.retriever = self.vector_db.as_retriever(search_kwargs={"k": 10})

        os.makedirs(output_dir, exist_ok=True)
        self.output_path = os.path.join(
            output_dir, f"output_{self.doc_id}.txt")
        # 清空或创建输出文件
        with open(self.output_path, "w", encoding="utf-8") as f:
            f.write(f"引用验证报告 - {self.doc_id}\n\n")

        self.llm = Tongyi(
            model=MODEL_CONFIGS['dashscope']['model'],
            api_key=MODEL_CONFIGS['dashscope']['api_key'])

        # 缓存已处理的文献
        self.processed_refs = {}

    def get_doc_hash(self, document):
        """结合内容和元数据生成唯一哈希"""
        content_hash = hashlib.md5(
            document.page_content.strip().encode('utf-8')).hexdigest()
        meta_hash = hashlib.md5(json.dumps(
            document.metadata, sort_keys=True).encode()).hexdigest()
        return f"{content_hash}_{meta_hash}"

    def load_hash_set(self):
        """加载哈希集合"""
        hashes = set()
        if os.path.exists(self.hash_file):
            with open(self.hash_file, 'r', encoding='utf-8') as f:
                for line in f:
                    hashes.add(line.strip())
        return hashes

    def append_hash_set(self, new_hashes):
        """追加新哈希到文件"""
        with open(self.hash_file, 'a', encoding='utf-8') as f:
            for h in new_hashes:
                f.write(h + "\n")

    def init_vector_db(self):
        """初始化向量数据库"""
        if os.path.exists(self.vector_db_dir):
            self.vector_db = FAISS.load_local(
                folder_path=self.vector_db_dir,
                embeddings=self.embeddings,
                allow_dangerous_deserialization=True
            )
            print(f"已加载现有向量数据库: {self.vector_db_dir}")
        else:
            self.create_vector_db()
            print(f"已创建新向量数据库: {self.vector_db_dir}")

    def create_vector_db(self):
        """创建新的向量数据库"""
        loader = PyPDFLoader(file_path=self.doc_path)
        documents = loader.load()

        xml_content = self.parser.grobid_extract_tei(self.doc_path)
        aps = AcademicPaperSplitter(xml_content)
        documents = aps.split_document()

        # 初始化哈希集合
        old_hashes = self.load_hash_set()
        new_docs = []
        new_hashes = []

        for doc in documents:
            h = self.get_doc_hash(doc)
            if h not in old_hashes:
                new_docs.append(doc)
                new_hashes.append(h)

        if new_docs:
            self.vector_db = FAISS.from_documents(new_docs, self.embeddings)
            self.append_hash_set(new_hashes)
            self.vector_db.save_local(self.vector_db_dir)
            print(f"添加了 {len(new_docs)} 个新文档块")
        else:
            # 如果没有新文档，创建空数据库
            self.vector_db = FAISS.from_documents([], self.embeddings)
            self.vector_db.save_local(self.vector_db_dir)
            print("没有发现新文档块")

    def download_if_needed(self, arxiv_doi):
        """按需下载文献"""
        try:
            pdf_path = os.path.join(self.download_dir, f"{arxiv_doi}.pdf")
            if os.path.exists(pdf_path):
                return pdf_path

            doi = arxiv_doi.split(":")[-1]
            s_result = self.arxiv_client.search_papers(doi)

            if not s_result:
                raise ValueError(f"未找到论文: {arxiv_doi}")

            success = self.arxiv_client.download_pdf(
                s_result[0]["pdf_link"], pdf_path)

            if success:
                print(f"成功下载: {arxiv_doi} → {pdf_path}")
                return pdf_path
            else:
                raise RuntimeError(f"下载失败: {arxiv_doi}")

        except Exception as e:
            raise RuntimeError(f"处理文献 {arxiv_doi} 失败: {str(e)}")

    def extract_refer_text_by_faiss(self, ref_entry):
        """
        使用faiss（retriever）进行检索，获取最相关正文片段
        """
        metadata = self.parser.extract_metadata(self.doc_path)
        query = f"""查询正文及附录中关于引用如下参考文献的所有段落
        title: {ref_entry['title']}
        authors: {ref_entry['authors']}
        doi: {ref_entry['doi']}
        """
        docs = self.retriever.get_relevant_documents(
            query=query, metadata={'title': metadata['title']})
        refer_text = [doc.page_content for doc in docs]
        return refer_text

    def verify_citation_by_chain(self, references, callback=None):
        """
        多引用多context逐条判别（基于向量检索）。
        :param references: list of reference dicts
        :param callback: 可选回调函数，用于实时显示结果
        """
        results = []

        for ref in references:
            # 跳过非arXiv文献
            if not (ref.get("journal") and ref.get("journal").lower() == "arxiv"):
                if callback:
                    callback(f"[跳过] 非arXiv文献: {ref.get('title')}\n")
                continue

            if not ref.get("doi"):
                if callback:
                    callback(f"[跳过] 缺少DOI: {ref.get('title')}\n")
                continue

            # 避免重复处理同一文献
            ref_key = ref["doi"]
            if ref_key in self.processed_refs:
                results.extend(self.processed_refs[ref_key])
                if callback:
                    callback(f"[缓存] 已处理文献: {ref.get('title')}\n")
                continue

            try:
                ref_path = self.download_if_needed(ref["doi"])
                refer_abstract = self.parser.extract_abstract(ref_path) or ""
            except Exception as e:
                error_msg = f"❌ 处理文献 {ref.get('title', '未知')} 时出错: {str(e)}\n"
                if callback:
                    callback(error_msg)
                with open(self.output_path, "a", encoding="utf-8") as f:
                    f.write(error_msg)
                continue

            # 检索相关段落
            refer_texts = self.extract_refer_text_by_faiss(ref)

            if not refer_texts:
                msg = f"❗️未找到引用: {ref['title']}\n"
                if callback:
                    callback(msg)
                with open(self.output_path, "a", encoding="utf-8") as f:
                    f.write(msg)
                continue

            ref_results = []
            for idx, context in enumerate(refer_texts):
                # 验证引用
                result = self.verify_single_citation(
                    context,
                    ref['title'],
                    ref['authors'],
                    refer_abstract
                )

                # 解析结果
                output_text = result.strip()
                is_related = "相关" in output_text.split("\n")[0]

                # 记录结果
                result_entry = {
                    "method": "vector_retrieval",
                    "ref_title": ref['title'],
                    "ref_authors": ref['authors'],
                    "context_idx": idx + 1,
                    "context": context,
                    "verification_result": output_text,
                    "is_related": is_related
                }
                ref_results.append(result_entry)

                # 输出到回调和文件
                output_msg = f"【{ref['title']}】段落{idx+1}: {output_text}\n"
                if callback:
                    callback(output_msg)
                with open(self.output_path, "a", encoding="utf-8") as f:
                    f.write(f"【向量检索】{ref['title']}段落{idx+1}\n{context}: {output_text}\n\n")

            # 缓存结果
            self.processed_refs[ref_key] = ref_results
            results.extend(ref_results)

        return results

    def verify_citation(self, references, callback=None):
        """
        使用grobid进行tei解析，并提取参考文献（基于精确位置）。
        :param references: list of reference dicts
        :param callback: 可选回调函数，用于实时显示结果
        """
        results = []

        for ref in references:
            if not (ref.get("journal") and ref.get("journal").lower() == "arxiv"):
                if callback:
                    callback(f"[跳过] 非arXiv文献: {ref.get('title')}\n")
                continue

            if not ref.get("doi"):
                if callback:
                    callback(f"[跳过] 缺少DOI: {ref.get('title')}\n")
                continue

            # 避免重复处理同一文献
            ref_key = ref["doi"]
            if ref_key in self.processed_refs:
                results.extend(self.processed_refs[ref_key])
                if callback:
                    callback(f"[缓存] 已处理文献: {ref.get('title')}\n")
                continue

            try:
                ref_path = self.download_if_needed(ref["doi"])
                refer_abstract = self.parser.extract_abstract(ref_path) or ""
            except Exception as e:
                error_msg = f"❌ 处理文献 {ref.get('title', '未知')} 时出错: {str(e)}\n"
                if callback:
                    callback(error_msg)
                with open(self.output_path, "a", encoding="utf-8") as f:
                    f.write(error_msg)
                continue

            # 找到论文中引用参考文献的段落
            try:
                ext_list = self.parser.extract_refer_text(
                    self.doc_path, ref.get('ref_id'))
            except Exception as e:
                if callback:
                    callback(f"提取引用文本失败: {str(e)}\n")
                ext_list = []

            if not ext_list:
                msg = f"❗️未找到直接引用: {ref.get('title')}\n"
                if callback:
                    callback(msg)
                with open(self.output_path, "a", encoding="utf-8") as f:
                    f.write(msg)
                continue

            ref_results = []
            for idx, context in enumerate(ext_list):
                # 验证引用
                result = self.verify_single_citation(
                    context,
                    ref['title'],
                    ref['authors'],
                    refer_abstract
                )

                # 解析结果
                output_text = result.strip()
                is_related = "相关" in output_text.split("\n")[0]

                # 记录结果
                result_entry = {
                    "method": "grobid_extraction",
                    "ref_title": ref['title'],
                    "ref_authors": ref['authors'],
                    "context_idx": idx + 1,
                    "context": context,
                    "verification_result": output_text,
                    "is_related": is_related
                }
                ref_results.append(result_entry)

                # 输出到回调和文件
                output_msg = f"\n【{ref['title']}】精确位置{idx+1}: {output_text}\n"
                if callback:
                    callback(output_msg)
                with open(self.output_path, "a", encoding="utf-8") as f:
                    f.write(f"【精确位置】{ref['title']}段落{idx+1}:\n\n{context}\nresult:\n {output_text}\n\n")

            # 缓存结果
            self.processed_refs[ref_key] = ref_results
            results.extend(ref_results)

        return results

    def verify_single_citation(self, context, title, authors, abstract):
        """验证单个引用（共享逻辑）"""
        prompt_template = PromptTemplate(
            input_variables=["context", "title", "authors", "abstract"],
            template="""请判断下面论文正文中的引用内容，从论文内容、相关性等方面判断是否真正参考了后面给出的文献。
论文正文引用片段：
\"\"\"{context}\"\"\"

参考文献条目：
标题：{title}
作者：{authors}
摘要：{abstract}

请输出“相关”或“不相关”，并给出简短理由。"""
        )

        # 使用新的 RunnableSequence 方法
        citation_verifier = prompt_template | self.llm

        return citation_verifier.invoke({
            "context": context,
            "title": title,
            "authors": authors,
            "abstract": abstract
        })