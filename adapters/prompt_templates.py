# verifier/prompt_templates.py

VERIFY_CITATION_PROMPT = """
请根据以下参考文献信息，验证论文中引用的准确性：

待验证引用：{citation_text}
参考文献数据：{reference_data}

要求：
1. 检查引用内容是否与参考文献一致（标题、作者、年份等关键信息）
2. 标注不一致的具体部分（如作者姓名拼写错误、年份不符等）
3. 输出JSON格式结果，包含验证状态（"verified": true/false）和差异说明（"difference": 字符串）
"""

SCORE_CRITERIA = """
根据以下验证结果，按1-5分评分（5分为完全一致，1分为严重不符）：
验证状态：{verified}
差异说明：{difference}
评分理由：{reason}
"""
