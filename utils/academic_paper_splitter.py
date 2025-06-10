from xml.etree import ElementTree as ET
import nltk
import re
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

# 初始化NLTK资源
nltk.download('punkt', quiet=True)


class AcademicPaperSplitter:
    def __init__(self, xml_content, max_chunk_size=1024, chunk_overlap=200):
        self.ns = {'tei': 'http://www.tei-c.org/ns/1.0'}
        self.root = ET.fromstring(xml_content)
        self.max_chunk_size = max_chunk_size
        self.chunk_overlap = chunk_overlap
        self.section_hierarchy = []
        self.current_figure = None
        self.current_table = None
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.max_chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", " ", ""]
        )

    def extract_metadata(self):
        """提取文档级元数据"""
        title = self.root.find('.//tei:title[@level="a"]', self.ns).text
        authors = [author.text for author in self.root.findall(
            './/tei:author', self.ns)]
        doi = self.root.find('.//tei:idno[@type="arXiv"]', self.ns).text

        return {
            'title': title,
            'authors': ', '.join(authors),
            'doi': doi,
            'source': 'TEI_XML'
        }

    def process_element(self, element, current_text, chunks):
        """递归处理XML元素"""
        tag = element.tag.split('}')[-1] if '}' in element.tag else element.tag

        # 处理章节标题
        if tag == 'head':
            section_title = ''.join(element.itertext()).strip()
            section_level = self.determine_section_level(section_title)
            self.section_hierarchy = self.section_hierarchy[:section_level]
            self.section_hierarchy.append(section_title)

        # 处理段落
        elif tag == 'p':
            paragraph = ''.join(element.itertext()).strip()
            if paragraph:
                current_text.append(paragraph)

        # 处理公式
        elif tag == 'formula':
            formula_text = ''.join(element.itertext()).strip()
            if formula_text:
                formula_id = element.attrib.get(
                    '{http://www.w3.org/XML/1998/namespace}id', '')
                formula_chunk = f"FORMULA [{formula_id}]: {formula_text}"
                current_text.append(formula_chunk)

        # 处理图表
        elif tag == 'figure':
            fig_id = element.attrib.get(
                '{http://www.w3.org/XML/1998/namespace}id', '')
            label = element.find('.//tei:label', self.ns)
            fig_desc = element.find('.//tei:figDesc', self.ns)

            label_text = label.text if label is not None else f"Figure {fig_id}"
            desc_text = fig_desc.text if fig_desc is not None else ''

            self.current_figure = f"FIGURE [{label_text}]: {desc_text}"
            # 递归处理图表内的文本
            for child in element:
                self.process_element(child, current_text, chunks)
            self.current_figure = None

        # 处理表格
        elif tag == 'table':
            # 简化表格处理
            self.current_table = "TABLE PRESENT"
            # 递归处理表格内的文本
            for child in element:
                self.process_element(child, current_text, chunks)
            self.current_table = None

        # 处理引用
        elif tag == 'ref':
            ref_type = element.attrib.get('type', '')
            ref_target = element.attrib.get('target', '')

            if ref_type == 'bibr':
                citation = f"[CITATION: {ref_target}]"
                current_text.append(citation)
            elif ref_type == 'figure' and self.current_figure:
                current_text.append(self.current_figure)

        # 递归处理子元素
        for child in element:
            self.process_element(child, current_text, chunks)

    def determine_section_level(self, title):
        """确定章节层级"""
        # 基于标题前缀判断层级
        if re.match(r'^[IVXLCDM]+\.', title):  # 罗马数字
            return 0
        elif re.match(r'^[A-Z]\.', title):     # 大写字母
            return 1
        elif re.match(r'^\d+\.', title):        # 数字
            return 2
        return len(self.section_hierarchy)  # 保持当前层级

    def semantic_chunking(self, text):
        """基于语义的分块方法"""
        # 先按句子分割
        sentences = nltk.sent_tokenize(text)

        chunks = []
        current_chunk = []
        current_length = 0

        for sentence in sentences:
            # 保留公式上下文
            if re.search(r'FORMULA \[|\bFig\.', sentence):
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                    current_chunk = []
                    current_length = 0
                chunks.append(sentence)
                continue

            # 添加到当前块
            if current_length + len(sentence) <= self.max_chunk_size:
                current_chunk.append(sentence)
                current_length += len(sentence) + 1  # +1 for space
            else:
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                current_chunk = [sentence]
                current_length = len(sentence)

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks

    def split_document(self):
        """主分割方法"""
        metadata = self.extract_metadata()
        body = self.root.find('.//tei:body', self.ns)

        all_text = []
        chunks = []

        if body is not None:
            self.process_element(body, all_text, chunks)

        full_text = "\n\n".join(all_text)

        # 语义分割
        semantic_chunks = self.semantic_chunking(full_text)

        # 对过大的块进行二次分割
        final_chunks = []
        for chunk in semantic_chunks:
            if len(chunk) > self.max_chunk_size * 1.5:
                sub_chunks = self.text_splitter.split_text(chunk)
                final_chunks.extend(sub_chunks)
            else:
                final_chunks.append(chunk)

        # 创建文档对象
        documents = []
        for i, chunk in enumerate(final_chunks):
            # 添加结构化元数据
            chunk_metadata = metadata.copy()
            chunk_metadata.update({
                'chunk_index': i,
                'section': " > ".join(self.section_hierarchy) if self.section_hierarchy else 'Abstract',
                'section_level': len(self.section_hierarchy)
            })
            documents.append(
                Document(page_content=chunk, metadata=chunk_metadata))

        return documents


if __name__ == "__main__":
    # 使用示例
    xml_content = """您的XML内容"""
    splitter = AcademicPaperSplitter(xml_content)
    chunks = splitter.split_document()
