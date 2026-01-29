###### Tools
import re
from typing import List

from tests.openai_sdk import AgentLlm


def add(a:int,b:int):
    """
    加法工具
    :param a: int
    :param b: int
    :return: int
    """
    return int(a) + int(b)

class ToolExecutor:
    def __init__(self):
        self.tools = {}

    def register_tool(self,tool):
        self.tools[tool.__name__] = tool

    def get_tool(self,tool_name):
        return self.tools[tool_name]

    def get_available_tools(self):
        return "\n".join([name+":"+tool.__doc__ for name,tool in self.tools.items()])

tool_executor = ToolExecutor()
tool_executor.register_tool(add)
#########

######## Prompt
REACT_DEFAULT_PROMPT = """
请注意，你是一个有能力调用外部工具的智能助手。

可用工具如下:
{tools}

请严格按照以下格式进行回应:

Thought: 你的思考过程，用于分析问题、拆解任务和规划下一步行动。
Action: 你决定采取的行动，必须是以下格式之一:
- `{{tool_name}}[{{tool_input}}]`:调用一个可用工具。
- `Finish[最终答案]`:当你认为已经获得最终答案时。
- 当你收集到足够的信息，能够回答用户的最终问题时，你必须在Action:字段后使用 Finish[最终答案] 来输出最终答案。

现在，请开始解决以下问题:
Question: {question}
History: {history}
"""

class ReactAgent:
    def __init__(self,llm_client:AgentLlm,max_steps=5):
        self.llm_client = llm_client
        self.max_steps = max_steps
        self.history = []

    def _parse_response(self,response):
        thought_match = re.search(r"Thought: (.*)", response)
        action_match = re.search(r"Action: (.*)", response)
        thought = thought_match.group(1).strip() if thought_match else None
        action = action_match.group(1).strip() if action_match else None
        return thought, action

    def _parse_action(self,action):
        match = re.match(r"(\w+)\[(.*)\]", action)
        if match:
            return match.group(1), match.group(2)
        return None, None

    def run(self,question:str):
        self.history = []
        current_step = 0
        while current_step < self.max_steps:
            current_step += 1
            print("step:", current_step)
            history = "\n".join(self.history)
            available_tools = tool_executor.get_available_tools()
            prompt = REACT_DEFAULT_PROMPT.format(tools=available_tools,question=question,history=history)
            messages = [{"role":"user","content":prompt}]
            response = self.llm_client.invoke(messages)
            if not response:
                print('Error Response')
                break
            else:
                thought,action = self._parse_response(response)
                if thought:
                    print("思考:",thought)
                if not action:
                    print('Error Action')
                    break
                if action.startswith("Finish"):
                    final_answer = re.match(r"Finish\[(.*)\]", action).group(1)
                    print(f"🎉 最终答案: {final_answer}")
                    return final_answer
                tool_name,tool_input = self._parse_action(action)
                tool_function = tool_executor.get_tool(tool_name)
                if not tool_function:
                    observation = f"错误:未找到名为 '{tool_name}' 的工具。"
                else:
                    observation = tool_function(*eval(tool_input))
                print(f"👀 观察: {observation}")
                self.history.append("Action:"+action)
                self.history.append(f"Observation: {observation}")
        print('Max Step,Stop Working!')
        return None

if __name__ == '__main__':
    llm = AgentLlm()
    react = ReactAgent(llm_client=llm)
    result = react.run("调用add工具相加3+2")