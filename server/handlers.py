"""
业务处理层（核心协调者）
负责：
1. 加载会话记忆 (User Memory)
2. 构建完整上下文
3. 调用 Agent 执行（Agent 内部有 TaskContextMemory）
4. 保存会话记忆
"""

import asyncio
import logging
from typing import AsyncGenerator, Optional, Dict, Callable
from dataclasses import dataclass

from agent.agent import Agent
from config import config
from server.memory import MemoryManager, ContextBuilder

logger = logging.getLogger(__name__)


@dataclass
class StreamMessage:
    """流式消息"""
    role: str
    output: dict
    is_complete: bool = False
    is_error: bool = False
    error_message: str = ""


class TaskHandler:
    """任务处理器"""
    
    def __init__(self):
        self.memory_manager = MemoryManager()
    
    async def execute_task(
        self,
        user_id: str,
        query: str,
        request_config: Optional[Dict] = None,
        enable_memory: bool = True
    ) -> AsyncGenerator[StreamMessage, None]:
        """
        执行任务（完整流程）
        
        Args:
            user_id: 用户 ID
            query: 用户查询
            request_config: 请求级配置覆盖
            enable_memory: 是否启用记忆
        
        Yields:
            StreamMessage: 流式消息
        """
        logger.info(f"⚙️  开始执行任务 - user_id: {user_id}, enable_memory: {enable_memory}")
        logger.debug(f"   查询: {query[:100]}...")  # 只记录前100个字符
        
        # 1. 加载历史记忆 (User Memory)
        history = []
        enhanced_query = query
        
        if enable_memory:
            try:
                logger.debug(f"📚 加载用户记忆: {user_id}")
                history = await self.memory_manager.load_history(
                    user_id, 
                    limit=config.memory.user_max_history
                )
                logger.info(f"✅ 加载了 {len(history)} 条历史记录")
                
                # 构建包含历史的上下文
                enhanced_query = ContextBuilder.build(
                    query, 
                    history, 
                    max_context_length=config.memory.user_max_history
                )
                logger.debug(f"🔗 增强查询长度: {len(enhanced_query)} 字符")
            except Exception as e:
                logger.warning(f"⚠️  加载记忆失败: {e}", exc_info=True)
                # 继续执行，不阻断流程
        
        # 2. 构建 Agent 配置
        logger.debug(f"🔧 构建 Agent 配置")
        agent_config = self._build_agent_config(enhanced_query, request_config)
        
        # 3. 执行任务（Agent 内部使用 TaskContextMemory）
        logger.info(f"🚀 执行 Agent 任务")
        assistant_response_parts = []  # 收集响应用于保存记忆
        
        async for stream_msg in self._run_agent(agent_config):
            logger.debug(f"📤 收到流消息 - role: {stream_msg.role}, is_complete: {stream_msg.is_complete}, is_error: {stream_msg.is_error}")
            
            # 收集响应内容
            if not stream_msg.is_error and not stream_msg.is_complete:
                assistant_response_parts.append(
                    f"{stream_msg.role}: {stream_msg.output}"
                )
            
            yield stream_msg
            
            # 如果出错或完成，跳出
            if stream_msg.is_error or stream_msg.is_complete:
                break
        
        # 4. 保存记忆 (User Memory)
        if enable_memory and assistant_response_parts:
            logger.debug(f"💾 保存任务记忆 - user_id: {user_id}")
            try:
                assistant_response = "\n".join(assistant_response_parts)
                await self.memory_manager.save_interaction(
                    user_id=user_id,
                    user_query=query,  # 保存原始 query，不是 enhanced
                    assistant_response=assistant_response
                )
            except Exception as e:
                logger.warning(f"⚠️ 保存记忆失败: {e}")
    
    async def _run_agent(
        self,
        agent_config: Dict
    ) -> AsyncGenerator[StreamMessage, None]:
        """运行 Agent"""
        queue: asyncio.Queue = asyncio.Queue()
        
        async def send_callback(role: str, intermediate_output: dict, is_complete: bool = False):
            await queue.put(StreamMessage(
                role=role,
                output=intermediate_output,
                is_complete=is_complete
            ))
        
        async def agent_task():
            try:
                agent = Agent(send_callback, agent_config)
                await agent.process()
                # 不再需要额外的complete消息，summarizer已经标记is_complete=True
            except Exception as e:
                logger.error(f"❌ Agent 执行错误: {e}", exc_info=True)
                await queue.put(StreamMessage(
                    role="error",
                    output={"error": str(e)},
                    is_error=True,
                    error_message=str(e)
                ))
            finally:
                await queue.put(None)  # 结束标记
        
        # 启动 Agent 任务
        asyncio.create_task(agent_task())
        
        # 流式返回结果
        while True:
            item = await queue.get()
            if item is None:
                break
            yield item
    
    def _build_agent_config(
        self,
        query: str,
        request_config: Optional[Dict] = None
    ) -> Dict:
        """构建 Agent 配置"""
        # 获取配置（请求覆盖 > 环境变量 > 默认值）
        planning_override = request_config.get("planning", {}) if request_config else {}
        grounding_override = request_config.get("grounding", {}) if request_config else {}
        
        planning = config.get_model_config("planning", planning_override)
        grounding = config.get_model_config("grounding", grounding_override)
        
        return {
            "user_query": query,
            # Planning 模型配置
            "planning_model": planning.get("model", ""),
            "planning_api_key": planning.get("api_key", ""),
            "planning_base_url": planning.get("base_url", ""),
            # Grounding 模型配置
            "grounding_model": grounding.get("model", ""),
            "grounding_api_key": grounding.get("api_key", ""),
            "grounding_base_url": grounding.get("base_url", ""),
            # 任务配置
            "max_iterations": config.memory.max_iterations,
            "task_max_memory_steps": config.memory.task_max_memory_steps,
        }


# 全局实例
task_handler = TaskHandler()
