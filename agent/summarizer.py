"""
任务总结器 (Summarizer)
根据任务执行历史生成最终总结

- 输入：TaskContextMemory（包含 user_query 和 dispatcher_actions）
- 输出：可读的总结 + 执行步骤列表
"""

import json
import platform
from typing import Dict, Tuple
from openai import OpenAI

from .memory import TaskContextMemory


class Summarizer:
    """
    任务总结器
    
    根据用户原始需求和执行的动作历史生成最终总结
    """
    
    def __init__(self, api_key: str, base_url: str, model: str):
        """
        初始化总结器
        
        Args:
            api_key: API 密钥
            base_url: API 基础 URL
            model: 模型名称
        """
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
        )
        self.model = model
        self.controlled_os = platform.system()
    
    def _get_system_prompt(self) -> str:
        return """你是一个任务总结专家。

你的职责是根据用户的原始需求和任务执行过程，生成一份清晰、简洁的执行总结。

## 总结要求

1. **结果导向**：首先说明任务是否完成，以及完成情况
2. **步骤清晰**：列出关键执行步骤，但不要过于冗长
3. **问题说明**：如果有失败或异常，简要说明原因

## 输出格式

```json
{
    "summary": "一句话总结任务执行情况",
    "success": true/false,
}
```

注意：只输出 JSON，不要有其他文字。"""

    def _build_context(self, task_memory: TaskContextMemory) -> str:
        """构建上下文信息"""
        lines = []
        
        # 用户原始输入
        lines.append("## 用户原始输入")
        lines.append(task_memory.user_query)
        
        # 当前规划
        if task_memory.current_plan:
            lines.append("\n## 执行规划")
            lines.append(task_memory.current_plan)
        
        # 执行动作历史（使用所有历史，不只是最近3条）
        actions = task_memory.get_all_actions()
        lines.append(f"\n## 执行动作 (共 {task_memory.current_step} 步)")
        
        for i, action in enumerate(actions, 1):
            action_type = action.action_type
            params = action.params
            
            if action_type == "execute":
                executor = params.get("executor", "unknown")
                action_desc = params.get("action", "")
                lines.append(f"  ✓ 步骤 {i}: [{executor}] {action_desc}")
            elif action_type == "modify_plan":
                lines.append(f"  → 步骤 {i}: 修改规划")
                new_plan = params.get("new_plan", "")
                if new_plan:
                    lines.append(f"     新规划: {new_plan[:100]}...")
            elif action_type == "end":
                lines.append(f"  ■ 步骤 {i}: 任务结束")
        
        return "\n".join(lines)
    
    def _parse_response(self, content: str) -> Dict:
        """解析 LLM 响应"""
        try:
            json_str = content.replace("```json", "").replace("```", "").strip()
            return json.loads(json_str)
        except json.JSONDecodeError:
            # 解析失败时返回默认结构
            return {
                "success": False,
                "summary": "任务总结生成失败",
            }
    
    def generate(self, task_memory: TaskContextMemory) -> Tuple[str, Dict]:
        """
        生成任务总结
        
        Args:
            task_memory: 任务上下文记忆
        
        Returns:
            (原始响应, 解析后的总结字典)
        """
        context = self._build_context(task_memory)
        
        messages = [
            {
                "role": "system",
                "content": self._get_system_prompt()
            },
            {
                "role": "user",
                "content": f"请根据以下任务执行信息生成总结：\n\n{context}"
            }
        ]
        
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=messages
        )
        
        content = completion.choices[0].message.content
        summary_dict = self._parse_response(content)
        
        return content, summary_dict
    
    def __call__(self, task_memory: TaskContextMemory) -> Dict:
        """
        生成任务总结（简化调用）
        
        Args:
            task_memory: 任务上下文记忆
        
        Returns:
            总结字典
        """
        _, summary_dict = self.generate(task_memory)
        return summary_dict
