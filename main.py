import argparse
from verifier.citation_verifier_system import CitationVerificationSystem

if __name__ == "__main__":
    # 添加参数解析器
    parser = argparse.ArgumentParser(description='论文引用验证系统')
    # 添加 --doc_path 参数，用于指定文档路径
    parser.add_argument('--doc_path', type=str, required=True,
                        help='文档路径，例如：path/to/your/document.pdf')
    parser.add_argument('--download_dir', type=str, required=True,
                        help='文档保存路径，例如：path/to/your/download_dir')
    parser.add_argument('--output_dir', type=str, required=True,
                        help='文档保存路径，例如：path/to/your/download_dir')
    args = parser.parse_args()

    system = CitationVerificationSystem(
        download_dir=args.download_dir, doc_path=args.doc_path, output_dir=args.output_dir)
    # 解析出所有的参考文献
    references = system.parser.extract_references(system.doc_path)
    # 验证引用文
    system.verify_citation(references)
