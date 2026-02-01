"""
任务上下文记忆 (Task Context Memory)
存储当前任务执行过程中的完整上下文

- 生命周期：单个任务内，任务结束后保留在 temp 目录
- 内容：用户原始输入、完整规划、所有历史动作
- 访问时机：Agent 内部循环（Planner 使用），读取时筛选最近 N 条
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any


class DispatcherAction:
    """Dispatcher 执行的动作记录"""
    
    def __init__(self, action_type: str, params: Dict):
        """
        Args:
            action_type: 动作类型 ("execute", "modify_plan", "end")
            params: 动作参数
        """
        self.action_type = action_type
        self.params = params
        self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        return {
            "action_type": self.action_type,
            "params": self.params,
            "timestamp": self.timestamp
        }
    
    @staticmethod
    def from_dict(data: Dict) -> "DispatcherAction":
        """从字典恢复"""
        action = DispatcherAction(
            action_type=data["action_type"],
            params=data["params"]
        )
        action.timestamp = data.get("timestamp", datetime.now().isoformat())
        return action


class TaskContextMemory:
    """
    任务上下文记忆
    
    存储当前任务执行过程中的完整上下文信息
    
    记录内容：
    - 用户原始输入（不可变）
    - 完整规划（可更新）
    - 所有历史动作（完整保存，读取时筛选）
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
        
        # 所有历史动作（完整保存）
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
    
    def add_dispatcher_action(self, action_type: str, params: Dict):
        """
        记录 Dispatcher 的动作（完整保存）
        
        Args:
            action_type: 动作类型 ("execute", "modify_plan", "end")
            params: 动作参数
        """
        self.current_step += 1
        
        action = DispatcherAction(action_type, params)
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
    
    def to_dict(self) -> Dict:
        """转换为字典（完整保存）"""
        return {
            "task_id": self.task_id,
            "user_query": self.user_query,  # 用户原始输入
            "current_plan": self.current_plan,  # 当前规划
            "current_step": self.current_step,
            "created_at": self.created_at,
            "dispatcher_actions": [action.to_dict() for action in self.dispatcher_actions],
            "saved_info": self.saved_info,
        }
    
    def _save_to_file(self):
        """保存到临时文件为 memory.json"""
        try:
            memory_path = os.path.join(self.run_folder, 'memory.json')
            with open(memory_path, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            # 静默处理保存失败
            pass
