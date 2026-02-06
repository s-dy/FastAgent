import json
import re
from typing import Union, Dict, List


def json_output_parser(text: str) -> Union[Dict, List]:
    """
    解析JSON输出
    """
    # 1. 移除注释（处理 // 和 /* */ 样式注释）
    text = re.sub(r'//.*?\n', '\n', text)  # 单行注释
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)  # 多行注释

    # 2. 移除 Markdown 代码块标记（如果有的话）
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```', '', text)

    # 3. 修复常见的 JSON 格式问题
    text = text.replace("'", '"')  # 替换单引号为双引号
    text = re.sub(r'(\w+):', r'"\1":', text)  # 为未加引号的键添加引号

    # 4. 使用第三方库处理更复杂的格式问题
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"JSON 解析失败: {str(e)} | 原始文本: {text[:200]}...")
