# CitationVerifierAgent

国科大杭高院高级人工智能课程大作业（论文引用查证）

项目说明：

- 本项目基于 Arxiv 上的论文进行验证，验证的论文可以是任意的论文，只要是 Arxiv 上的论文都可以。
- 本项目有使用 Grobid 进行论文解析，
- 目前只支持使用 DashScope 的 API 进行验证。
- 使用

## 0. Setup

克隆项目，拉取项目代码，并创建conda环境

```bash
git clone https://github.com/SandyZ17/CitationVerifierAgent.git 
cd CitationVerifierAgent
# 创建 conda 环境
conda create -n citation_verifier python=3.10 -y
conda activate citation_verifier
# 安装依赖
pip instal -r requirements.txt
```

启动 Grobid Docker 服务

```bash
docker run -d -p 8070:8070 --name grobid grobid/grobid:0.8.1
```

Macos

```bash
docker run -d -p 8070:8070 --name grobid grobid/grobid:0.8.1
```

## 1. Build && Run

在根目录下创建一个 `.env` 文件，内容如下（目前只支持使用通义千问API）：

```text
API_KEY=sk-***********
EMBEDDING_MODEL=text-embedding-v2
LLM_MODEL=qwen-max
```

运行

```bash
python main.py --doc_path your_test_pdf_path --download_dir your_arxiv_doc_dir --output_dir your_result_output_path --verify_type simple
```

参数说明

- `doc_path`: 待验证的论文路径
- `download_dir`: 下载的 Arxiv 论文的目录
- `output_dir`: 输出结果的目录
- `verify_type`: 验证类型，可选 `simple` 或 `advanced`，默认为 `simple`，simple模式使用 Grobid 进行论文引用部分解析再使用 API 进行验证，advanced模式使用 RAG 增强索引查询参考文献，使用 Langchain 框架构建任务链验证。

##
