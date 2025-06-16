import argparse
from verifier.citation_verifier_system import CitationVerificationSystem
from verifier.citation_verify_langchain_ver import CitationVerificationLangchainVer

if __name__ == "__main__":
    # 添加参数解析器
    parser = argparse.ArgumentParser(description='论文引用验证系统')
    # 添加 --doc_path 参数，用于指定文档路径
    parser.add_argument('--verify_type', type=str, required=True,
                        help='验证模式，例如：chain/simple')
    parser.add_argument('--doc_path', type=str, required=True,
                        help='文档路径，例如：path/to/your/document.pdf')
    parser.add_argument('--download_dir', type=str, required=True,
                        help='文档保存路径，例如：path/to/your/download_dir')
    parser.add_argument('--output_dir', type=str, required=True,
                        help='文档保存路径，例如：path/to/your/download_dir')
    args = parser.parse_args()

    # 解析出所有的参考文献
    if args.verify_type == "simple":
        system = CitationVerificationSystem(
            download_dir=args.download_dir, doc_path=args.doc_path, output_dir=args.output_dir)
        references = system.parser.extract_references(system.doc_path)
        print("✅ 使用普通模型进行验证")
        system.verify_citation(references)
    else:
        sys = CitationVerificationLangchainVer(
            download_dir=args.download_dir, doc_path=args.doc_path, output_dir=args.output_dir)
        references = sys.parser.extract_references(
            sys.doc_path)
        print("✅ 使用链路模型进行验证")
        sys.verify_citation_by_chain(references)
