import hashlib
import os
import json
import shutil

import utils
from clients.arxiv_client import ArxivClient
from config.settings import MODEL_CONFIGS, GROBID_URL, LLM_PLATFORM
from parsers.grobid_parser import GrobidParser as gp

from langchain_community.vectorstores import FAISS
from langchain_community.docstore.document import Document
from langchain_core.prompts import PromptTemplate
from langchain_community.document_loaders.generic import GenericLoader
from langchain_community.document_loaders.parsers import GrobidParser as langchain_grobid_parser

import utils.refer_parser


class CitationVerificationLangchainVer:
    def __init__(self, download_dir, doc_path, output_dir):
        if not os.path.isfile(doc_path):
            raise FileNotFoundError(f"路径填写错误{doc_path}")

        # 初始化配置
        self.doc_path = doc_path

        self.doc_id = os.path.splitext(
            os.path.basename(self.doc_path))[0]
        self.output_dir = os.path.join(output_dir, self.doc_id)
        shutil.rmtree(self.output_dir, ignore_errors=True)
        # 设置output_path
        self.result_path = os.path.join(
            self.output_dir, f"result_{self.doc_id}.txt")
        self.repeat_path = os.path.join(
            self.output_dir, f"repeat_{self.doc_id}.txt")
        self.error_path = os.path.join(
            self.output_dir, f"error_{self.doc_id}.txt")
        # 初始化解析器
        self.parser = gp(grobid_url=GROBID_URL)
        self.langchain_grobid_parser = langchain_grobid_parser(
            segment_sentences=False, grobid_server=f"{GROBID_URL}/api/processFulltextDocument")
        self.loader = GenericLoader.from_filesystem(
            self.doc_path,
            glob="*",
            suffixes=[".pdf"],
            parser=langchain_grobid_parser(segment_sentences=False),
        )
        # 初始化arxiv客户端
        self.arxiv_client = ArxivClient()
        self.download_dir = download_dir
        os.makedirs(self.download_dir, exist_ok=True)

        self.init_llm_platform()

        # 初始化向量数据库列表
        self.init_vector_db()
        self.retriever = self.vector_db.as_retriever(search_kwargs={"k": 5})

        os.makedirs(self.output_dir, exist_ok=True)
        # 初始化处理过的引用列表
        self.processed_refs = {}

    def init_llm_platform(self):
        # 初始化 LLM
        if LLM_PLATFORM == "openai":
            from langchain_community.embeddings import OpenAIEmbeddings
            import langchain_community.llms.openai as openai
            self.embeddings = OpenAIEmbeddings(
                model=MODEL_CONFIGS['dashscope']['embedding_model'],
                api_key=MODEL_CONFIGS['dashscope']['api_key'])
            self.llm = openai.OpenAI(
                model=MODEL_CONFIGS['openai']['model'],
                api_key=MODEL_CONFIGS['openai']['api_key'])
        elif LLM_PLATFORM == "tongyi":
            from langchain_community.embeddings import DashScopeEmbeddings
            import langchain_community.llms.tongyi as tongyi
            # 初始化嵌入模型
            self.embeddings = DashScopeEmbeddings(
                model=MODEL_CONFIGS['dashscope']['embedding_model'],
                dashscope_api_key=MODEL_CONFIGS['dashscope']['api_key'])
            self.llm = tongyi.Tongyi(
                model=MODEL_CONFIGS['dashscope']['model'],
                api_key=MODEL_CONFIGS['dashscope']['api_key'])
        elif LLM_PLATFORM == "qianfan":
            from langchain_community.embeddings.baidu_qianfan_endpoint import QianfanEmbeddingsEndpoint
            import langchain_community.llms.baidu_qianfan_endpoint as qianfan
            # 初始化嵌入模型
            self.embeddings = QianfanEmbeddingsEndpoint(
                model=MODEL_CONFIGS['dashscope']['embedding_model'],
                api_key=MODEL_CONFIGS['dashscope']['api_key'])
            self.llm = qianfan.QianfanLLMEndpoint(
                model=MODEL_CONFIGS['qianfan']['model'],
                api_key=MODEL_CONFIGS['qianfan']['api_key'])
        else:
            raise ValueError(f"Unsupported LLM platform: {LLM_PLATFORM}")

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
        """初始化向量数据库，并返回向量库列表"""
        doc = self.loader.load()
        # 向量数据库路径
        vector_db_dir_tmp = f"faiss_index_{self.doc_id}"
        # 如果vector_db存在，则强制删除已存在的db，创建新的db
        if os.path.exists(vector_db_dir_tmp):
            shutil.rmtree(vector_db_dir_tmp)
        # 创建新的向量数据库
        self.vector_db = FAISS.from_documents(doc, self.embeddings)
        self.vector_db.save_local(vector_db_dir_tmp)
        # 输出创建向量数据库的进度
        print(f"Created vector database for {self.doc_id}")

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
        query = f"""查询正文及附录中关于引用参考文献[{utils.refer_parser.increment_id(ref_entry['ref_id'])}]的所有段落，参考文献详细信息如下：
        title: {ref_entry['title']}
        authors: {ref_entry['authors']}
        doi: {ref_entry['doi']}
        """
        docs = self.retriever.get_relevant_documents(
            query=query, metadata={'title': ref_entry['title']})
        refer_text = [doc.page_content for doc in docs]
        return refer_text

    def verify_citation_by_chain(self, references):
        """
        多引用多context逐条判别（基于向量检索）。
        :param references: list of reference dicts
        """
        results = []

        for ref in references:
            if not ref.get("doi"):
                print(f"[跳过] 缺少DOI: {ref.get('title')}")
                continue

            # 缓存结果
            # 避免重复处理同一文献，并将重复的参考文献写入repeat.txt中
            ref_key = ref["doi"]
            if ref_key in self.processed_refs:
                self.append_hash_set([self.get_doc_hash(ref_path)])
                with open(self.repeat_path, "a", encoding="utf-8") as f:
                    f.write(
                        f"查找到重复参考文献: {ref.get('title')} (DOI: {ref_key})\n")
                continue
            self.processed_refs[ref_key] = []

            # 跳过非arXiv文献
            if not (ref.get("journal") and ref.get("journal").lower() == "arxiv"):
                print(f"[跳过] 非arXiv文献: {ref.get('title')}")
                continue

            try:
                ref_path = self.download_if_needed(ref["doi"])
                refer_abstract = self.parser.extract_abstract(
                    ref_path) or ""
            except Exception as e:
                print(f"处理文献 {ref.get('title', '未知')} 时出错: {str(e)}")
                with open(self.error_path, "a", encoding="utf-8") as f:
                    f.write(f"❌ 处理失败: {ref['title']} - {str(e)}\n")
                continue

            # 检索相关段落
            refer_texts = self.extract_refer_text_by_faiss(ref)

            if not refer_texts:
                msg = f"❗️未找到引用: {ref['title']}"
                print(msg)
                with open(self.error_path, "a", encoding="utf-8") as f:
                    f.write(msg + "\n")
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

                # 输出到控制台和文件
                print(f"【{ref['title']}】段落{idx+1}: {output_text}")
                seg = '*' * 60
                with open(self.result_path, "a", encoding="utf-8") as f:
                    f.write(
                        f"【向量检索】{ref['title']}段落{idx+1}\n{context}: {output_text}\n {seg} \n")

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

请输出“相关/不相关/不确定”，并给出简短理由。"""
        )

        # 使用新的 RunnableSequence 方法
        citation_verifier = prompt_template | self.llm

        return citation_verifier.invoke({
            "context": context,
            "title": title,
            "authors": authors,
            "abstract": abstract
        })
