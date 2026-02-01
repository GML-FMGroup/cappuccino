"""
上下文构建器
将历史对话整合到当前查询中
"""

from typing import List, Dict, Optional


class ContextBuilder:
    """上下文构建器"""
    
    @staticmethod
    def build(
        current_query: str,
        history: List[Dict],
        max_context_length: int = 5
    ) -> str:
        """
        构建包含历史的完整上下文
        
        Args:
            current_query: 当前用户查询
            history: 历史对话列表 [{"role": "user/assistant", "content": "..."}]
            max_context_length: 最大上下文轮数
        
        Returns:
            str: 完整的查询上下文
        """
        if not history:
            return current_query
        
        # 限制历史长度
        recent_history = history[-max_context_length:] if len(history) > max_context_length else history
        
        # 构建上下文
        context_parts = ["# 历史对话上下文\n"]
        
        for idx, msg in enumerate(recent_history, 1):
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            
            if role == "user":
                context_parts.append(f"[{idx}] 用户: {content}")
            elif role == "assistant":
                # 简化 assistant 响应，只保留关键信息
                summary = ContextBuilder._summarize_response(content)
                context_parts.append(f"[{idx}] 助手: {summary}")
        
        context_parts.append("\n# 当前任务")
        context_parts.append(current_query)
        
        return "\n".join(context_parts)
    
    @staticmethod
    def _summarize_response(response: str, max_length: int = 100) -> str:
        """
        简化 assistant 响应
        避免上下文过长
        """
        if len(response) <= max_length:
            return response
        
        # 简单截断，保留开头
        return response[:max_length] + "..."
    
    @staticmethod
    def extract_key_info(history: List[Dict]) -> Dict:
        """
        从历史中提取关键信息
        用于智能上下文构建（未来扩展）
        
        Returns:
            Dict: {"mentioned_files": [...], "tasks": [...], ...}
        """
        # TODO: 实现智能信息提取
        # - 提取提到的文件名
        # - 提取任务列表
        # - 提取重要实体
        return {
            "mentioned_files": [],
            "tasks": [],
            "entities": []
        }
