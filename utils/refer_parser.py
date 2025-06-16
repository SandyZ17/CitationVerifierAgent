import re


class PaperStruct:
    def __init__(self, ref_id, title, authors, journal, abstract, references, doi, year):
        self.ref_id = ref_id
        self.title = title
        self.authors = authors
        self.journal = journal
        self.doi = doi
        self.abstract = abstract
        self.references = references
        self.year = year

    def __str__(self):
        return f"Title: {self.title}\nAuthors: {self.authors}\nAbstract: {self.abstract}\nReferences: {self.references}\nDOI: {self.doi}"


def parse_ieee_reference(ref_text):
    # 优化正则表达式，兼容中英文引号，且让 doi 前空格匹配更灵活
    pattern = re.compile(
        r'^(?P<authors>.+?),\s*["“](?P<title>.+?)["”]\s*,\s*(?P<date>\w+\s+\d{1,2},\s+\d{4}),\s*arXiv:\s*(?P<arxiv_id>[\d\.]+)\.?\s*doi:\s*(?P<doi>\S+)',
        re.UNICODE
    )
    match = pattern.match(ref_text)
    if not match:
        return None

    return {
        "authors": match.group("authors"),
        "title": match.group("title"),
        "date": match.group("date"),
        "arxiv_id": match.group("arxiv_id"),
        "doi": match.group("doi")
    }


def increment_id(identifier):
    # 使用正则提取数字部分（允许数字在任意位置）
    match = re.search(r'\d+', identifier)
    if not match:
        return identifier + "1"  # 无数字时在末尾添加1

    num_str = match.group()
    start_idx, end_idx = match.span()

    # 数字加1并转换为字符串
    new_num = str(int(num_str) + 1)

    # 处理前导零（可选）
    # 如果原数字有前导零且新数字长度相同，则保留前导零格式
    if num_str.startswith('0') and len(new_num) == len(num_str):
        return identifier[:start_idx] + new_num.zfill(len(num_str)) + identifier[end_idx:]

    # return identifier[:start_idx] + new_num + identifier[end_idx:]
    return new_num
