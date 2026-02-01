"""
记忆管理器
统一的记忆加载/保存接口
"""

from typing import List, Dict, Optional
from .storage import create_storage, StorageBackend


class MemoryManager:
    """记忆管理器（单例）"""
    
    _instance: Optional['MemoryManager'] = None
    _storage: Optional[StorageBackend] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._storage is None:
            # 默认使用 SQLite 存储
            self._storage = create_storage()
    
    @classmethod
    def initialize(cls, db_path: str = "./data/memory.db"):
        """初始化 SQLite 存储"""
        instance = cls()
        instance._storage = create_storage(db_path=db_path)
    
    async def load_history(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Dict]:
        """
        加载用户历史对话
        
        Args:
            user_id: 用户 ID
            limit: 最多加载多少条历史
        
        Returns:
            List[Dict]: 历史消息列表
        """
        return await self._storage.load_history(user_id, limit)
    
    async def save_interaction(
        self,
        user_id: str,
        user_query: str,
        assistant_response: str,
        metadata: Optional[Dict] = None
    ):
        """
        保存一轮对话
        
        Args:
            user_id: 用户 ID
            user_query: 用户查询
            assistant_response: 助手响应
            metadata: 额外元数据（执行时间、状态等）
        """
        # 保存用户消息
        await self._storage.save_message(user_id, {
            "role": "user",
            "content": user_query
        })
        
        # 保存助手响应
        response_msg = {
            "role": "assistant",
            "content": assistant_response
        }
        if metadata:
            response_msg["metadata"] = metadata
        
        await self._storage.save_message(user_id, response_msg)
    
    async def clear_history(self, user_id: str):
        """清空用户历史"""
        await self._storage.clear_history(user_id)


# 全局实例
memory_manager = MemoryManager()
