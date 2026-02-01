"""
规划器 (Planner)
统一的任务规划与决策组件

- 初始模式 (plan): 根据用户查询生成初始规划
- 执行模式 (dispatch): 根据当前状态决定下一步动作
"""

import os
import json
import platform
from typing import Tuple, List, Dict, Optional
from openai import OpenAI

from .utils import get_base64_screenshot
from .memory import TaskContextMemory


class Planner:
    """
    统一的任务规划器
    
    两种模式：
    1. plan(): 初始化时生成任务规划
    2. dispatch(): 执行过程中决定下一步动作
    """
    
    def __init__(self, api_key: str, base_url: str, model: str, run_folder: str):
        """
        初始化规划器
        
        Args:
            api_key: API 密钥
            base_url: API 基础 URL
            model: 模型名称
            run_folder: 运行目录
        """
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
        )
        self.model = model
        self.controlled_os = platform.system()
        self.run_folder = run_folder

    # ==================== 初始规划模式 ====================
    
    def _get_plan_system_prompt(self) -> str:
        """获取初始规划的系统提示"""
        return f"""你是一个任务规划专家，负责将用户的需求分解为可执行的任务步骤。

## 系统信息
- 当前操作系统: {self.controlled_os}

## 规划原则

1. **任务分解**：将复杂需求拆分为清晰、独立的子任务
2. **操作顺序**：确保任务按正确的逻辑顺序排列
3. **具体明确**：每个任务描述要具体，避免模糊表述
4. **可验证性**：每个任务完成后应有明确的验证标准

## 特殊规则

- 需要生成文件（Word、Excel、PDF 等）时，使用代码生成而非手动操作软件

## 输出格式

```json
{{
    "thinking": "分析用户需求，说明规划思路",
    "plan": "完整的执行计划描述，包含所有步骤"
}}
```

## 示例

用户需求: "在B站搜索apex视频并播放"

```json
{{
    "thinking": "要在B站播放apex视频，需要：1）打开B站网站 2）在搜索框搜索apex 3）点击视频播放",
    "plan": "1. 打开浏览器并访问 https://www.bilibili.com/ 2. 在搜索框中输入 'apex' 并搜索 3. 点击第一个视频进行播放"
}}
```

注意：只输出 JSON，不要有其他文字。"""

    def plan(self, query: str) -> Tuple[str, str, str]:
        """
        生成初始任务规划
        
        Args:
            query: 用户查询
        
        Returns:
            (原始响应, 思考过程, 规划内容)
        """
        # 获取当前屏幕截图
        base64_screenshot = get_base64_screenshot(self.run_folder)
        
        # 构建消息：包含文本和截图
        messages = [
            {
                "role": "system",
                "content": self._get_plan_system_prompt(),
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": query},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{base64_screenshot}"},
                    },
                ],
            }
        ]
        
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=messages
        )
        
        content = completion.choices[0].message.content
        thinking, plan = self._parse_plan_response(content)
        
        return content, thinking, plan
    
    def _parse_plan_response(self, content: str) -> Tuple[str, str]:
        """解析规划响应"""
        try:
            json_str = content.replace("```json", "").replace("```", "").strip()
            json_dict = json.loads(json_str)
            return json_dict.get("thinking", ""), json_dict.get("plan", "")
        except json.JSONDecodeError:
            return "规划解析失败", content

    # ==================== 执行决策模式 ====================
    
    def _get_executor_description(self) -> str:
        """获取执行器描述"""
        executor_list_path = os.path.join(os.path.dirname(__file__), "executors", "executor_list.json")
        with open(executor_list_path, 'r', encoding='utf-8') as f:
            executors = json.load(f)
        
        lines = []
        for executor in executors:
            lines.append(f"- {executor['name']}: {executor['description']}")
        
        return "\n".join(lines)

    def _get_dispatch_system_prompt(self) -> str:
        """获取执行决策的系统提示"""
        return f"""你是任务执行决策者，根据当前状态决定下一步行动。

## 系统信息
- 当前操作系统: {self.controlled_os}

## 可用执行器

{self._get_executor_description()}

## 动作类型

1. **execute** - 执行具体操作
   参数:
   - executor: 执行器名称 (interact_executor, code_executor, wait)
   - action: 具体操作描述 (不需要涉及具体坐标，语义化描述即可)

2. **save_info** - 保存重要信息到记忆
   参数:
   - key: 信息的键（如 "歌曲名称"、"联系人ID" 等）
   - value: 信息的值
   
   使用场景：当前步骤获取了后续步骤需要使用的信息时，应该保存到记忆中

3. **modify_plan** - 修改总规划
   参数:
   - new_plan: 修改后的规划（字符串，包含所有步骤）

4. **end** - 任务完成，结束执行
   参数: (无)

## 决策原则

1. **基于现状**：根据当前截图、历史动作和总规划决策
2. **循序渐进**：每次只执行一个具体动作
3. **灵活调整**：如果发现规划不符合实际，使用 modify_plan
4. **及时结束**：当所有步骤完成时，使用 end

## 输出格式

```json
{{
    "thinking": "分析当前状态，说明决策原因",
    "action": {{
        "type": "execute|save_info|modify_plan|end",
        "params": {{
            // execute:
            "executor": "执行器名称",
            "action": "操作描述",
            
            // save_info:
            "key": "信息键名",
            "value": "信息值",
            
            // modify_plan:
            "new_plan": "修改后的规划",
            
            // end: 无params
        }}
    }}
}}
```"""
    
    def _get_dispatch_user_prompt(
        self, 
        task_memory: TaskContextMemory,
        task_max_memory_steps: int = 3
    ) -> str:
        """构建执行决策的用户提示"""
        prompt_parts = ["## 当前状态"]
        
        # 用户原始输入
        prompt_parts.extend([
            "",
            "### 用户原始输入",
            task_memory.user_query
        ])
        
        # 当前规划
        if task_memory.current_plan:
            prompt_parts.extend([
                "",
                "### 当前规划",
                task_memory.current_plan
            ])
        
        # 已保存的信息
        saved_info_str = task_memory.get_saved_info()
        if saved_info_str != "暂无已保存信息":
            prompt_parts.extend([
                "",
                "### 已保存的信息",
                saved_info_str
            ])
        
        # 已保存的信息
        saved_info_str = task_memory.get_saved_info()
        if saved_info_str != "暂无已保存信息":
            prompt_parts.extend([
                "",
                "### 已保存的信息",
                saved_info_str
            ])
        
        recent_actions = task_memory.get_recent_actions(task_max_memory_steps)
        if recent_actions:
            prompt_parts.append("\n### 最近的动作历史")
            for i, action in enumerate(recent_actions, 1):
                prompt_parts.append(f"{i}. {action.action_type}")
                if action.action_type == "execute":
                    prompt_parts.append(f"   执行器: {action.params.get('executor')}")
                    prompt_parts.append(f"   操作: {action.params.get('action')}")
                elif action.action_type == "modify_plan":
                    prompt_parts.append(f"   新规划: {action.params.get('new_plan')}")
        else:
            prompt_parts.append("\n### 历史动作")
            prompt_parts.append("暂无（这是第一步）")
        
        prompt_parts.extend([
            "",
            "## 任务",
            "根据以上信息，决定下一步动作。"
        ])
        
        return "\n".join(prompt_parts)

    def _parse_dispatch_response(self, content: str) -> Tuple[str, Dict]:
        """解析执行决策响应"""
        try:
            json_str = content.replace("```json", "").replace("```", "").strip()
            json_dict = json.loads(json_str)
            return json_dict.get("thinking", ""), json_dict.get("action", {})
        except json.JSONDecodeError:
            return "解析失败", {}

    def dispatch(
        self, 
        task_memory: TaskContextMemory,
        task_max_memory_steps: int = 3,
        min_pixels: int = 3136, 
        max_pixels: int = 12845056
    ) -> Tuple[str, str, Dict]:
        """
        决定下一步动作
        
        Args:
            task_memory: 任务上下文记忆
            task_max_memory_steps: 最多使用几条历史动作
            min_pixels: 图片最小像素
            max_pixels: 图片最大像素
        
        Returns:
            (原始响应, 思考过程, 动作字典)
        """
        # 获取当前屏幕截图
        base64_screenshot = get_base64_screenshot(self.run_folder)

        # 构建消息
        messages = [
            {
                "role": "system",
                "content": self._get_dispatch_system_prompt(),
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": self._get_dispatch_user_prompt(task_memory, task_max_memory_steps)},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{base64_screenshot}"},
                    },
                ],
            }
        ]
        
        # 调用 LLM
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=messages
        )
        
        content = completion.choices[0].message.content
        thinking, action = self._parse_dispatch_response(content)

        return content, thinking, action
