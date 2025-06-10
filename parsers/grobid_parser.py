from lxml import etree
from grobid_client.grobid_client import GrobidClient


class GrobidParser:
    def __init__(self, grobid_url="http://localhost:8070"):
        self.grobid_client = GrobidClient(grobid_server=grobid_url)

    def grobid_extract_tei(self, doc_path):
        """
        使用GROBID提取PDF中的TEI XML
        :param pdf_path: PDF文件路径
        :return: TEI XML字符串
        """
        try:
            _, _, xml_content = self.grobid_client.process_pdf(
                service="processFulltextDocument", pdf_file=doc_path, generateIDs=False, consolidate_header=True, consolidate_citations=False, include_raw_citations=True,
                include_raw_affiliations=True, tei_coordinates=True, segment_sentences=False)
        except Exception as e:
            print(f"[ERROR] Grobid 解析全文错误: {e}")
            return None
        return xml_content

    def grobid_extract_tei_batch(self,
                                 input_path="./resources/test_pdf",
                                 output_dir="./resources/test_output",
                                 n=10,
                                 generateIDs=False,
                                 consolidate_header=True,
                                 consolidate_citations=False,
                                 include_raw_citations=False,
                                 include_raw_affiliations=False,
                                 tei_coordinates=False,
                                 segment_sentences=False,
                                 force=True,
                                 verbose=False):
        """
        使用GROBID提取PDF中的TEI XML
        :param pdf_path: PDF文件路径
        :return: TEI XML字符串
        """
        try:
            self.grobid_client.process(service="processFulltextDocument",
                                       input_path=input_path,
                                       output=output_dir,
                                       n=n,
                                       generateIDs=generateIDs,
                                       consolidate_header=consolidate_header,
                                       consolidate_citations=consolidate_citations,
                                       include_raw_citations=include_raw_citations,
                                       include_raw_affiliations=include_raw_affiliations,
                                       tei_coordinates=tei_coordinates,
                                       segment_sentences=segment_sentences,
                                       force=force,
                                       verbose=verbose)
        except Exception as e:
            print(f"[错误] 提取TEI XML失败: {e}")
            return ""

    def extract_references_batch(self, input_path, output_path):
        """
        使用GROBID提取PDF中的参考文献
        :param pdf_path: PDF文件路径
        :return: 参考文献列表
        """
        try:
            self.grobid_client.process(service="processHeaderDocument",
                                       input_path=input_path,
                                       output=output_path,
                                       consolidate_header=True,
                                       include_raw_citations=True,
                                       include_raw_affiliations=True,
                                       force=True,)
            # 解析XML
            root = etree.fromstring(input_path.encode('utf-8'))
            ns = {'tei': 'http://www.tei-c.org/ns/1.0'}
            # 参考文献列表
            bibs = []
            for idx, bib in enumerate(root.xpath('//tei:listBibl/tei:biblStruct', namespaces=ns)):
                text = ''.join(bib.itertext()).strip().replace('\n', ' ')
                bibs.append({"content": text, "ref_id": idx+1})
            return bibs
        except Exception as e:
            print(f"[错误] 提取参考文献失败: {e}")
            return []

    def extract_references(self, doc_path):
        """
        使用GROBID提取PDF中的参考文献
        :param pdf_path: PDF文件路径
        :return: 参考文献列表
        """
        try:
            _, _, xml_content = self.grobid_client.process_pdf(
                service="processReferences", pdf_file=doc_path, generateIDs=False, consolidate_header=False, consolidate_citations=False, include_raw_citations=True, include_raw_affiliations=True, tei_coordinates=False, segment_sentences=False)

            # 解析出 XML References 内容
            root = etree.fromstring(xml_content.encode('utf-8'))
            ns = {'tei': 'http://www.tei-c.org/ns/1.0'}

            bibl_list = []

            for bib in root.xpath('//tei:biblStruct', namespaces=ns):
                xml_id = bib.get('{http://www.w3.org/XML/1998/namespace}id')
                if not xml_id:
                    continue

                # 提取常见元数据
                # 作者
                authors = []
                for author in bib.xpath('.//tei:author', namespaces=ns):
                    name = []
                    for fn in author.findall('.//tei:forename', namespaces=ns):
                        name.append(fn.text)
                    surname = author.find('.//tei:surname', namespaces=ns)
                    if surname is not None:
                        name.append(surname.text)
                    authors.append(' '.join(name))

                # 期刊
                journal_el = bib.find(
                    './/tei:monogr//tei:title', namespaces=ns)
                journal = journal_el.text if journal_el is not None else ""

                # DOI
                doi = ""

                # 标题
                title_el = bib.find(
                    './/tei:analytic//tei:title', namespaces=ns)
                if title_el is None:
                    title_el = bib.find(
                        './/tei:monogr//tei:title', namespaces=ns)
                    d = bib.find(
                        './/tei:monogr//tei:idno[@type="arXiv"]', namespaces=ns)
                    if d is not None:
                        doi = d.text
                        journal = "arXiv"

                title = title_el.text

                # 出版年份
                year_el = bib.find('.//tei:date', namespaces=ns)
                year = year_el.get('when') if (year_el is not None and year_el.get(
                    'when')) else (year_el.text if year_el is not None else "")

                bibl_list.append({
                    "ref_id": xml_id,
                    "authors": authors,
                    "title": title,
                    "journal": journal,
                    "year": year,
                    "doi": doi
                })
            return bibl_list
        except Exception as e:
            print(f"[错误] 提取参考文献失败: {e}")
            return []

    def extract_abstract_batch(self, input_dir, output_dir):
        """
        使用GROBID提取PDF中的摘要
        :param input_dir: 输入文件（通常为PDF文件）的目录路径
        :param output_dir: 处理结果输出的目录路径
        :return: 提取到的摘要文本，若提取失败则返回空字符串
        """
        try:
            # 调用GROBID客户端的process方法，使用processHeaderDocument服务处理输入文件
            # 该服务会解析文件头部信息，包含摘要等内容
            self.grobid_client.process(service="processHeaderDocument",
                                       input_path=input_dir,
                                       output=output_dir,
                                       consolidate_header=True,  # 合并页眉元数据
                                       include_raw_citations=True,  # 包含原始引用信息
                                       include_raw_affiliations=True,  # 包含原始机构信息
                                       force=True,)  # 强制处理文件
        except Exception as e:
            # 若调用GROBID服务过程中出现异常，打印错误信息并返回空字符串
            print(f"[错误] 提取摘要失败: {e}")
            return ""

        try:
            # 解析GROBID处理后输出的XML文件
            root = etree.parse(output_dir)
            # 定义命名空间，用于定位XML元素
            ns = {'tei': 'http://www.tei-c.org/ns/1.0'}
            # 使用XPath查询，查找所有符合条件的摘要节点
            ab_nodes = root.xpath('//tei:abstract', namespaces=ns)
            # 若存在摘要节点，提取第一个节点下的所有文本内容，去除首尾空格；否则返回空字符串
            abstract = ''.join(ab_nodes[0].itertext()
                               ).strip() if ab_nodes else ''
            return abstract
        except Exception as e:
            # 若解析XML文件过程中出现异常，打印错误信息并返回空字符串
            print(f"[错误] 解析XML失败: {e}")
            return ""

    def extract_abstract(self, pdf_path):
        """
        使用GROBID提取PDF中的摘要
        :param pdf_path: PDF文件路径
        :return: 提取到的摘要文本，若提取失败则返回空字符串
        """
        try:
            _, _, xml_content = self.grobid_client.process_pdf(service="processHeaderDocument", pdf_file=pdf_path, generateIDs=False, consolidate_header=True,
                                                               consolidate_citations=True, include_raw_citations=True, include_raw_affiliations=True, tei_coordinates=True, segment_sentences=True)
            # grobid解析文件成功
            print(f"[成功] grobid解析{pdf_path}成功")
            # 解析出 XML Abstract 内容
            root = etree.fromstring(xml_content.encode('utf-8'))
            ns = {'tei': 'http://www.tei-c.org/ns/1.0'}

            # 提取abstract部分
            abstracts = root.xpath('//tei:abstract', namespaces=ns)
            if abstracts:
                abstract_text = ''.join(abstracts[0].itertext()).strip()
                return abstract_text
            else:
                print("未检测到摘要部分！")
        except Exception as e:
            print(f"[错误] 提取摘要失败: {e}")
            return ""

    def extract_refer_text(self, doc_path, ref_id):
        """
        使用GROBID提取PDF中的指定引用的文本
        :param doc_path: PDF文件路径
        :param ref_id: 引用ID
        :return: 提取到的引用文本，若提取失败则返回空字符串
        """
        res = []
        # 调用GROBID客户端的process方法，使用processReferences服务处理输入文件
        xml_content = self.grobid_extract_tei(doc_path=doc_path)
        if not xml_content:
            return res
        # 解析出 XML References 内容
        root = etree.fromstring(xml_content.encode('utf-8'))
        ns = {'tei': 'http://www.tei-c.org/ns/1.0'}
        xpath_str = '//tei:p[.//tei:ref[@type="bibr" and @target="#{}"]]'.format(
            ref_id)
        paras = root.xpath(xpath_str, namespaces=ns)
        for p in paras:
            text = ''.join(p.itertext())
            res.append(text)
        return res


if __name__ == "__main__":
    pdf_path = "../data/test_pdf/2506.05336v1.pdf"
    parser = GrobidParser("http://localhost:8070")
    # abstract = parser.extract_abstract(pdf_path=pdf_path)
    # print(abstract)
    # bibs = parser.extract_references(doc_path=pdf_path)
    # print(bibs)

    res = parser.extract_refer_text(doc_path=pdf_path, ref_id="b4")
    print(res)
