import os
from typing import List, Dict

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

class AgentLlm:
    def __init__(self,model=None,api_key=None,base_url=None):
        self.model = model or os.getenv("QWEN_MODEL_NAME")
        api_key = api_key or os.getenv("QWEN_API_KEY")
        base_url = base_url or os.getenv("QWEN_BASE_URL")

        self.client = OpenAI(api_key=api_key,base_url=base_url)

    def invoke(self,messages:List[Dict[str,str]],temperature:float=0) -> str:
        # print('Strat Call LLM Model')
        try:
            response = self.client.chat.completions.create(model=self.model,messages=messages,temperature=temperature,stream=True)
            # print('LLM Model Call Success')
            collected_context = []
            for chunk in response:
                content = chunk.choices[0].delta.content or ""
                print(content,end="",flush=True)
                collected_context.append(content)
            print()
            return "".join(collected_context)
        except Exception as e:
            print(e)
            return ""

if __name__ == '__main__':
    llm = AgentLlm()
    exampleMessages = [
        {"role": "system", "content": "You are a helpful assistant that writes Python code."},
        {"role": "user", "content": "写一个快速排序算法"}
    ]

    print("--- 调用LLM ---")
    responseText = llm.invoke(exampleMessages)
    if responseText:
        print("\n\n--- 完整模型响应 ---")
        print(responseText)

