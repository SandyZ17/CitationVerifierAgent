import streamlit as st
import os
from verifier.citation_verifier_system import CitationVerificationSystem
from verifier.citation_verify_langchain_ver import CitationVerificationLangchainVer
from config.settings import CheckType

def main():
    st.title("论文引用验证系统")
    st.markdown("上传 PDF 文档并选择验证模式以验证参考文献。")

    # 初始化 session_state 用于存储历史验证结果
    if "verification_history" not in st.session_state:
        st.session_state.verification_history = []

    # 侧边栏用于输入参数
    with st.sidebar:
        st.header("设置")
        system_type = st.selectbox("选择验证系统", ["CitationVerificationSystem", "CitationVerificationLangchainVer"],
                                  help="选择使用的验证系统")
        verify_type = st.selectbox("验证模式", ["simple", "chain"], help="选择验证模式：simple（基于精确位置）或 chain（基于向量检索）")
        doc_file = st.file_uploader("上传 PDF 文档", type=["pdf"], help="上传需要验证引用的 PDF 文档")
        download_dir = st.text_input("文档下载路径", value="./downloads", help="指定下载参考文献的目录")
        output_dir = st.text_input("输出路径", value="./output", help="指定验证结果的输出目录")

    # 验证按钮
    if st.button("开始验证"):
        if not doc_file:
            st.error("请上传 PDF 文档！")
            return
        if not download_dir or not output_dir:
            st.error("请填写下载路径和输出路径！")
            return

        # 保存上传的 PDF 文件到临时路径
        temp_doc_path = os.path.join("temp", doc_file.name)
        os.makedirs("temp", exist_ok=True)
        with open(temp_doc_path, "wb") as f:
            f.write(doc_file.getbuffer())

        # 确保下载和输出目录存在
        os.makedirs(download_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)

        try:
            # 初始化验证系统
            if system_type == "CitationVerificationSystem":
                system = CitationVerificationSystem(
                    download_dir=download_dir,
                    doc_path=temp_doc_path,
                    output_dir=output_dir
                )
            else:  # CitationVerificationLangchainVer
                system = CitationVerificationLangchainVer(
                    download_dir=download_dir,
                    doc_path=temp_doc_path,
                    output_dir=output_dir
                )

            # 提取参考文献
            with st.spinner("正在提取参考文献..."):
                references = system.parser.extract_references(system.doc_path)
                st.success(f"提取到 {len(references)} 条参考文献")

            # 创建动态输出区域
            output_container = st.empty()

            def callback(message):
                # 追加新消息到历史记录
                st.session_state.verification_history.append(message)
                # 更新显示所有历史记录
                with output_container.container():
                    for hist_msg in st.session_state.verification_history:
                        if "❌" in hist_msg or "失败" in hist_msg:
                            st.error(hist_msg)
                        elif "❗️" in hist_msg:
                            st.warning(hist_msg)
                        elif "[跳过]" in hist_msg or "[重复]" in hist_msg or "[缓存]" in hist_msg:
                            st.info(hist_msg)
                        else:
                            st.write(hist_msg)

            if verify_type == "simple":
                st.info("✅ 使用精确位置（Grobid）模型进行验证")
                for i, ref in enumerate(references, 1):
                    with st.spinner(f"正在验证参考文献 {i}/{len(references)}: {ref.get('title', '未知标题')}..."):
                        system.verify_citation([ref], callback=callback)
            else:
                st.info("✅ 使用向量检索（FAISS）模型进行验证")
                for i, ref in enumerate(references, 1):
                    with st.spinner(f"正在验证参考文献 {i}/{len(references)}: {ref.get('title', '未知标题')}..."):
                        system.verify_citation_by_chain([ref], callback=callback)

            # 提供下载结果的选项
            output_file = os.path.join(output_dir, f"output_{system.doc_id}.txt") if hasattr(system, 'output_path') else \
                          os.path.join(output_dir, system.doc_id, f"result_{system.doc_id}.txt")
            if os.path.exists(output_file):
                with open(output_file, "rb") as f:
                    st.download_button(
                        label="下载验证结果",
                        data=f,
                        file_name=os.path.basename(output_file),
                        mime="text/plain"
                    )

        except Exception as e:
            st.error(f"验证过程中发生错误：{str(e)}")
        finally:
            # 清理临时文件
            if os.path.exists(temp_doc_path):
                os.remove(temp_doc_path)

if __name__ == "__main__":
    main()