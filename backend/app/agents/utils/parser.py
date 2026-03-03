import json
from typing import Any

def parse_json_response(raw_text: str) -> Any:
    """安全解析 LLM 返回的 JSON 文本，自动处理 Markdown 代码块"""
    text = raw_text.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()
    return json.loads(text)
