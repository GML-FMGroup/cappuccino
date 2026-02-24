"""
任务上下文记忆 (Task Context Memory)
存储当前任务执行过程中的完整上下文

- 生命周期：单个任务内，任务结束后保留在 temp 目录
- 内容：用户原始输入、完整规划、所有历史动作（包含MCP执行结果）
- 访问时机：Agent 内部循环（Planner 使用），读取时筛选最近 N 条
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any


class DispatcherAction:
    """Dispatcher 执行的动作记录"""
    
    def __init__(self, action_type: str, params: Dict, result: Optional[Dict] = None):
        """
        Args:
            action_type: 动作类型 ("execute", "modify_plan", "reply", "mcp", "save_info")
            params: 动作参数
            result: 动作执行结果（可选）
        """
        self.action_type = action_type
        self.params = params
        self.result = result  # 存储执行结果
        self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        return {
            "action_type": self.action_type,
            "params": self.params,
            "result": self.result,
            "timestamp": self.timestamp
        }
    
    @staticmethod
    def from_dict(data: Dict) -> "DispatcherAction":
        """从字典恢复"""
        action = DispatcherAction(
            action_type=data["action_type"],
            params=data["params"],
            result=data.get("result")
        )
        action.timestamp = data.get("timestamp", datetime.now().isoformat())
        return action
    
    def to_prompt_text(self) -> str:
        """转换为用于Prompt的文本格式"""
        lines = [f"[{self.action_type}]"]
        
        # 添加参数信息
        if self.params:
            if self.action_type == "mcp":
                # MCP动作特殊格式化
                protocol = self.params.get("protocol", "")
                mcp_action = self.params.get("action", "")
                success = self.params.get("success", False)
                lines[0] = f"[mcp:{protocol}:{mcp_action}] {'✓' if success else '✗'}"
                
                # 添加数据摘要
                data_summary = self.params.get("data_summary")
                if data_summary:
                    if isinstance(data_summary, dict):
                        for key, value in data_summary.items():
                            lines.append(f"  {key}: {value}")
                    else:
                        lines.append(f"  结果: {data_summary}")
                
                # 添加错误信息
                error = self.params.get("error")
                if error:
                    lines.append(f"  错误: {error}")
            elif self.action_type == "execute":
                lines.append(f"  操作: {self.params.get('action', '')}")
            elif self.action_type == "save_info":
                lines.append(f"  {self.params.get('key', '')}: {self.params.get('value', '')}")
            elif self.action_type == "modify_plan":
                lines.append(f"  新规划: {self.params.get('new_plan', '')[:100]}...")
            elif self.action_type == "reply":
                lines.append(f"  回复: {self.params.get('message', '')[:100]}...")
        
        return "\n".join(lines)


class TaskContextMemory:
    """
    任务上下文记忆
    
    存储当前任务执行过程中的完整上下文信息
    
    记录内容：
    - 用户原始输入（不可变）
    - 完整规划（可更新）
    - 所有历史动作（完整保存，读取时筛选，包含MCP执行结果）
    - 保存的重要信息（键值对）
    - 任务状态
    """
    
    def __init__(self, task_id: str, user_query: str, run_folder: str):
        """
        初始化任务上下文记忆
        
        Args:
            task_id: 任务唯一标识
            user_query: 用户原始输入（保持不变）
            run_folder: 运行目录（用于保存临时文件）
        """
        self.task_id = task_id
        self.user_query = user_query  # 用户原始输入（不可变）
        self.current_plan = ""  # 当前规划（由 Planner 生成，可更新）
        self.run_folder = run_folder
        
        # 所有历史动作（完整保存，包含execute/modify_plan/reply/mcp/save_info）
        self.dispatcher_actions: List[DispatcherAction] = []
        
        # 保存的重要信息（键值对）
        self.saved_info: Dict[str, str] = {}
        
        # 当前步骤数
        self.current_step = 0
        
        # 创建时间
        self.created_at = datetime.now().isoformat()
    
    def is_first_step(self) -> bool:
        """是否是第一步"""
        return self.current_step == 0
    
    def set_plan(self, plan: str):
        """
        设置/更新当前规划
        
        Args:
            plan: 规划内容
        """
        self.current_plan = plan
        self._save_to_file()
    
    def save_info(self, key: str, value: str):
        """保存重要信息到记忆
        
        Args:
            key: 信息的键（如 "歌曲名称"）
            value: 信息的值
        """
        self.saved_info[key] = value
        self._save_to_file()
    
    def get_saved_info(self, key: str = None) -> str:
        """获取保存的信息
        
        Args:
            key: 信息的键，如果为 None 则返回所有信息的格式化字符串
        
        Returns:
            单个信息值或所有信息的格式化字符串
        """
        if key:
            return self.saved_info.get(key, "")
        
        if not self.saved_info:
            return "暂无已保存信息"
        
        lines = []
        for k, v in self.saved_info.items():
            lines.append(f"- {k}: {v}")
        return "\n".join(lines)
    
    def add_dispatcher_action(self, action_type: str, params: Dict, result: Optional[Dict] = None):
        """
        记录 Dispatcher 的动作（完整保存）
        
        Args:
            action_type: 动作类型 ("execute", "modify_plan", "reply", "mcp", "save_info")
            params: 动作参数
            result: 动作执行结果（可选）
        """
        self.current_step += 1
        
        action = DispatcherAction(action_type, params, result)
        self.dispatcher_actions.append(action)
        
        # 完整保存，不再截断
        self._save_to_file()
    
    def get_recent_actions(self, n: int = 3) -> List[DispatcherAction]:
        """
        获取最近 n 条动作（读取时筛选）
        
        Args:
            n: 获取的动作数量，默认 3
        
        Returns:
            最近 n 条动作列表
        """
        return self.dispatcher_actions[-n:] if len(self.dispatcher_actions) > n else self.dispatcher_actions
    
    def get_all_actions(self) -> List[DispatcherAction]:
        """获取所有历史动作"""
        return self.dispatcher_actions
    
    def get_actions_by_type(self, action_type: str) -> List[DispatcherAction]:
        """
        获取特定类型的动作
        
        Args:
            action_type: 动作类型
        
        Returns:
            匹配的动作列表
        """
        return [action for action in self.dispatcher_actions if action.action_type == action_type]
    
    # ==================== MCP 相关接口 ====================
    
    def add_mcp_result(self, protocol: str, action: str, success: bool, 
                       data_summary: Any, error: Optional[str] = None):
        """
        添加MCP执行结果到记忆
        
        直接将MCP结果作为dispatcher_action存储，不再单独维护mcp_results字段
        
        Args:
            protocol: MCP协议名称（如 "filesystem"）
            action: 动作类型（如 "read", "write"）
            success: 是否执行成功
            data_summary: 结果数据摘要
            error: 错误信息（如果失败）
        """
        params = {
            "protocol": protocol,
            "action": action,
            "success": success,
            "data_summary": data_summary,
            "error": error
        }
        
        # 直接作为mcp类型的dispatcher_action存储
        self.add_dispatcher_action("mcp", params)
    
    def get_mcp_actions(self, protocol: Optional[str] = None, 
                        limit: Optional[int] = None) -> List[DispatcherAction]:
        """
        获取MCP类型的动作
        
        Args:
            protocol: 协议名称过滤，如果为None则返回所有MCP动作
            limit: 限制返回数量，默认无限制
        
        Returns:
            MCP动作列表
        """
        mcp_actions = [action for action in self.dispatcher_actions 
                       if action.action_type == "mcp"]
        
        # 按协议过滤
        if protocol:
            mcp_actions = [action for action in mcp_actions 
                          if action.params.get("protocol") == protocol]
        
        # 限制数量（返回最近的）
        if limit and len(mcp_actions) > limit:
            return mcp_actions[-limit:]
        
        return mcp_actions
    
    def get_mcp_summary_for_prompt(self, protocol: Optional[str] = None,
                                    limit: int = 5) -> str:
        """
        生成用于LLM Prompt的MCP结果摘要
        
        Args:
            protocol: 特定协议，如果为None则包含所有协议
            limit: 最多显示几条结果
        
        Returns:
            格式化的文本摘要
        """
        mcp_actions = self.get_mcp_actions(protocol=protocol, limit=limit)
        
        if not mcp_actions:
            return "暂无MCP执行结果"
        
        lines = ["### MCP执行历史"]
        
        for action in mcp_actions:
            lines.append(action.to_prompt_text())
        
        return "\n".join(lines)
    
    def has_mcp_results(self, protocol: Optional[str] = None) -> bool:
        """
        检查是否有MCP执行结果
        
        Args:
            protocol: 特定协议，如果为None则检查所有协议
        
        Returns:
            是否有结果
        """
        mcp_actions = self.get_mcp_actions(protocol=protocol)
        return len(mcp_actions) > 0
    
    def get_last_mcp_result(self, protocol: Optional[str] = None) -> Optional[DispatcherAction]:
        """
        获取最近的MCP结果
        
        Args:
            protocol: 特定协议，如果为None则返回任意协议的最近结果
        
        Returns:
            最近的MCP动作，如果没有则返回None
        """
        mcp_actions = self.get_mcp_actions(protocol=protocol)
        return mcp_actions[-1] if mcp_actions else None
    
    # ==================== 序列化接口 ====================
    
    def to_dict(self) -> Dict:
        """转换为字典（完整保存）"""
        return {
            "task_id": self.task_id,
            "user_query": self.user_query,
            "current_plan": self.current_plan,
            "current_step": self.current_step,
            "created_at": self.created_at,
            "dispatcher_actions": [action.to_dict() for action in self.dispatcher_actions],
            "saved_info": self.saved_info,
        }
    
    @staticmethod
    def from_dict(data: Dict, run_folder: str) -> "TaskContextMemory":
        """从字典恢复TaskContextMemory"""
        memory = TaskContextMemory(
            task_id=data.get("task_id", ""),
            user_query=data.get("user_query", ""),
            run_folder=run_folder
        )
        memory.current_plan = data.get("current_plan", "")
        memory.current_step = data.get("current_step", 0)
        memory.created_at = data.get("created_at", datetime.now().isoformat())
        memory.saved_info = data.get("saved_info", {})
        
        # 恢复dispatcher_actions
        memory.dispatcher_actions = [
            DispatcherAction.from_dict(action_data)
            for action_data in data.get("dispatcher_actions", [])
        ]
        
        return memory
    
    def _save_to_file(self):
        """保存到临时文件为 memory.json"""
        try:
            memory_path = os.path.join(self.run_folder, 'memory.json')
            with open(memory_path, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            # 静默处理保存失败
            pass
