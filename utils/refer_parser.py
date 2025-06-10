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
