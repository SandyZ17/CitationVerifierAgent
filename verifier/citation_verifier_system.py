import hashlib
import os

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


def get_hash(text):
    return hashlib.md5(text.strip().encode('utf-8')).hexdigest()


def load_hash_set(hash_file):
    hashes = set()
    if os.path.exists(hash_file):
        with open(hash_file, 'r', encoding='utf-8') as f:
            for line in f:
                hashes.add(line.strip())
    return hashes


def append_hash_set(hash_file, new_hashes):
    with open(hash_file, 'a', encoding='utf-8') as f:
        for h in new_hashes:
            f.write(h + "\n")


class CitationVerificationSystem:
    def __init__(self, download_dir, doc_path, output_dir):
        if not os.path.isfile(doc_path):
            raise FileNotFoundError(f"找不到文件: {doc_path}")
        self.doc_path = doc_path
        # 获取解析器
        self.parser = GrobidParser(grobid_url="http://localhost:8070")
        # 获取arxiv客户端及下载目录
        self.arxiv_client = ArxivClient()
        self.download_dir = download_dir
        os.makedirs(self.download_dir, exist_ok=True)
        # 初始化向量数据库
        # 如果存在本地向量数据库，则加载，否则创建一个新的空数据库
        self.vector_db = self.init_vector_db()
        # 初始化检索链
        self.retrieval_chain = None
        # 初始化输出路径
        os.makedirs(output_dir, exist_ok=True)
        self.output_path = os.path.join(output_dir, "output.txt")

    def init_vector_db(self):
        hash_file = "faiss_hashes.txt"
        # 初始化向量数据库，如果存在则加载并添加数据，否则创建一个新的空数据库
        if os.path.exists("faiss_index"):
            self.vector_db = FAISS.load_local(
                folder_path="faiss_index", embeddings=DashScopeEmbeddings(dashscope_api_key=MODEL_CONFIGS['dashscope']['api_key'], model=MODEL_CONFIGS['dashscope']['embedding_model']), allow_dangerous_deserialization=True)
            # 加载历史hash集合
            old_hashes = load_hash_set(hash_file)
            loader = PyPDFLoader(file_path=self.doc_path)
            doc = loader.load()
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=200, chunk_overlap=100)
            chunked_docs = text_splitter.split_documents(doc)

            # 做去重
            new_docs = []
            new_hashes = []
            for d in chunked_docs:
                h = get_hash(d.page_content)
                if h not in old_hashes:
                    old_hashes.add(h)
                    new_docs.append(d)
                    new_hashes.append(h)
            if new_docs:
                self.vector_db.add_documents(new_docs)
                append_hash_set(hash_file, new_hashes)
        else:
            self.create_vector_db()
        self.vector_db.save_local("faiss_index")

    def create_vector_db(self):
        hash_file = "faiss_hashes.txt"
        loader = PyPDFLoader(file_path=self.doc_path)
        doc = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=200, chunk_overlap=100)
        chunked_docs = text_splitter.split_documents(doc)

        # 去重
        old_hashes = load_hash_set(hash_file)
        new_docs = []
        new_hashes = []
        for d in chunked_docs:
            h = get_hash(d.page_content)
            if h not in old_hashes:
                old_hashes.add(h)
                new_docs.append(d)
                new_hashes.append(h)

        embeddings = DashScopeEmbeddings(
            model=MODEL_CONFIGS['dashscope']['embedding_model'],
            dashscope_api_key=MODEL_CONFIGS['dashscope']['api_key'])
        self.vector_db = FAISS.from_documents(new_docs, embeddings)
        append_hash_set(hash_file, new_hashes)

    def download_if_needed(self, arxiv_doi):
        try:
            pdf_path = os.path.join(self.download_dir, f"{arxiv_doi}.pdf")
            if os.path.exists(pdf_path):
                return pdf_path
            # 搜索论文
            doi = arxiv_doi.split(":")[-1]
            s_result = self.arxiv_client.search_papers(doi)
            if not s_result:
                return ValueError(f"[错误] 未找到论文: {arxiv_doi}")
            # 下载论文
            success = self.arxiv_client.download_pdf(
                s_result[0]["pdf_link"], pdf_path)
            print(f"[下载] 正在下载: {arxiv_doi} → {pdf_path}")
            if success:
                return pdf_path
            else:
                return ValueError(f"[失败] 下载失败: {arxiv_doi}")
        except Exception as e:
            return ValueError(f"[错误] 下载失败: {arxiv_doi} → {e}")

    def extract_refer_text_by_faiss(self, paper_chunk, ref_entry):
        prompt_template = PromptTemplate(
            input_variables=["paper_chunk", "title", "authors", "abstract"],
            template="""请判断下面论文正文中的引用内容，是否真正参考了后面给出的文献，并说明理由。
            论文正文引用片段：
            \"\"\"{paper_chunk}\"\"\"

            参考文献条目：
            标题：{title}
            作者：{authors}
            摘要：{abstract}

            请输出“相关”或“不相关”，并给出简短理由。"""
        )
        filled_prompt = prompt_template.format(
            paper_chunk=paper_chunk,
            title=ref_entry['title'],
            authors=ref_entry['authors'],
            abstract=ref_entry['abstract'])

    def verify_citation(self, references):
        # 提取文档中的参考文献
        for ref in references:
            arxiv_id = ref.get("journal")
            if not arxiv_id or arxiv_id.lower() != "arxiv":
                print(f"[跳过] 非 arXiv 参考文献: {ref.get('title')}")
                continue

            arxiv_doi = ref.get("doi")
            if arxiv_doi is None:
                print(f"[跳过] 未找到 DOI: {ref.get('title')}")
                continue
            try:
                pdf_path = self.download_if_needed(arxiv_doi=arxiv_doi)
            except:
                continue
            # 提取参考文献中的摘要
            refer_abstract = self.parser.extract_abstract(pdf_path)
            if not refer_abstract:
                print(f"[跳过] 未提取到摘要: {ref.get('title')}")
                continue

            # 找到论文中引用参考文献的段落
            ext_list = self.parser.extract_refer_text(
                pdf_path, ref.get('ref_id'))
            if not ext_list:
                with open(self.output_path, "a") as f:
                    f.write(
                        f"❗️未找到引用，可能存在冗余参考文献情况，请检查: {ref.get('title')}\n")
                continue
            for ext in ext_list:
                prompt_template = PromptTemplate(
                    input_variables=["paper_chunk",
                                     "title", "authors", "abstract"],
                    template="""请判断下面论文正文中的引用内容，是否真正参考了后面给出的文献，并说明理由。
论文正文引用片段：
\"\"\"{paper_chunk}\"\"\"

参考文献条目：
标题：{title}
作者：{authors}
摘要：{abstract}

请输出“相关”或“不相关”，并给出简短理由。""")
                filled_prompt = prompt_template.format(
                    paper_chunk=ext,
                    title=ref['title'],
                    authors=ref['authors'],
                    abstract=refer_abstract)
                llm = Tongyi(model="qwen-turbo",
                             api_key=MODEL_CONFIGS['dashscope']['api_key'])
                result = llm.invoke(filled_prompt)
                print(result)
        return
