import requests
# from config.settings import DEFAULT_MAX_RESULTS
import arxiv

DEFAULT_MAX_RESULTS = 10


class ArxivClient:
    def __init__(self):
        """初始化客户端，加载配置参数"""
        self.client = arxiv.Client()

    def search_papers(self, query, max_results=DEFAULT_MAX_RESULTS):
        """
        通过arxiv库搜索文献
        :param query: 搜索查询字符串（如作者、标题关键词等）
        :param max_results: 返回结果数量
        :return: 文献元数据列表（包含标题、作者、摘要、pdf链接等）
        """
        try:
            search = arxiv.Search(
                # query=query,
                id_list=[query],
                max_results=max_results,
                sort_by=arxiv.SortCriterion.Relevance,
                sort_order=arxiv.SortOrder.Descending
            )
            papers = []
            for result in self.client.results(search):
                papers.append({
                    "title": result.title,
                    "authors": [author.name for author in result.authors],
                    "summary": result.summary,
                    "pdf_link": result.pdf_url
                })
            return papers
        except Exception as e:
            print(f"arXiv搜索失败: {str(e)}")
            return []

    def download_pdf(self, pdf_url, save_path):
        """
        下载arXiv文献PDF
        :param pdf_url: arXiv PDF链接
        :param save_path: 保存路径（含文件名）
        :return: 下载成功状态
        """
        try:
            response = requests.get(pdf_url, stream=True)
            response.raise_for_status()
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
        except Exception as e:
            print(f"PDF下载失败: {str(e)}")
            return False


if __name__ == "__main__":
    # 测试示例
    client = ArxivClient()
    results = client.search_papers("1705.06950")
    print("搜索结果: ", results)
    if results:
        print("找到文献: ", results[0]["title"])
        success = client.download_pdf(
            results[0]["pdf_link"], "quantum_paper.pdf")
        print("下载状态: ", "成功" if success else "失败")
