"""
Agent 主流程编排

实现循环执行架构：
1. 初始化 TaskContextMemory
2. Loop (直到任务完成):
   - Planner: 生成或更新规划
   - Dispatcher: 分发执行子任务（Executor/MCP/Memory）
   - 更新 TaskContextMemory
"""

import json
import os
import platform
import logging
import time
import uuid
import asyncio
from functools import partial
from typing import Dict, Callable

from .memory import TaskContextMemory
from .planner import Planner
from .executor import Executor


class Agent:
    """
    Agent 任务执行引擎
    
    Parameters:
    - send_callback: 回调函数，用于发送中间结果
    - data: 配置数据字典，包含:
        - planning_model, planning_api_key, planning_base_url
        - grounding_model, grounding_api_key, grounding_base_url
        - user_query
        - max_iterations (可选，默认 10)
        - max_retry_per_task (可选，默认 3)
    """

    def __init__(self, send_callback: Callable, data: Dict):
        self.send_callback = send_callback
        self.data = data
        
        # 系统信息
        self.controlled_os = platform.system()
        
        # 创建运行目录
        temp_base = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'temp')
        self.run_folder = os.path.join(temp_base, time.strftime("%Y%m%d-%H%M%S"))
        os.makedirs(self.run_folder, exist_ok=True)
        os.environ["RUN_FOLDER"] = self.run_folder
        
        # 初始化日志
        self.logger = self._setup_logger()
        
        # 任务配置
        self.max_iterations = data.get("max_iterations", 10)
        self.max_retry_per_task = data.get("max_retry_per_task", 3)
        self.task_max_memory_steps = data.get("task_max_memory_steps", 10)
        
        # 初始化任务上下文记忆
        self.task_id = str(uuid.uuid4())[:8]
        self.task_memory = TaskContextMemory(
            task_id=self.task_id,
            user_query=data["user_query"],
            run_folder=self.run_folder
        )
        
        # 初始化各组件
        self._init_components()
        
        self.logger.info(f"Agent 初始化完成 - task_id: {self.task_id}")
    
    def _setup_logger(self) -> logging.Logger:
        """设置日志"""
        logger = logging.getLogger(f"Agent-{self.controlled_os}")
        logger.setLevel(logging.DEBUG)
        
        file_handler = logging.FileHandler(
            os.path.join(self.run_folder, 'agent.log'),
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        )
        logger.addHandler(file_handler)
        logger.propagate = False
        
        return logger
    
    def _init_components(self):
        """初始化各组件"""
        # Planning model 配置 (用于 planner)
        planning_config = {
            "api_key": self.data["planning_api_key"],
            "base_url": self.data["planning_base_url"],
            "model": self.data["planning_model"]
        }
        
        # Grounding model 配置 (用于 executor)
        grounding_config = {
            "api_key": self.data["grounding_api_key"],
            "base_url": self.data["grounding_base_url"],
            "model": self.data["grounding_model"]
        }
        
        # 初始化 Planner (统一规划和分发功能)
        self.planner = Planner(
            api_key=planning_config["api_key"],
            base_url=planning_config["base_url"],
            model=planning_config["model"],
            run_folder=self.run_folder
        )
        
        # 初始化 Executor (使用 grounding 模型)
        self.executor = Executor(
            grounding_config=grounding_config,
            run_folder=self.run_folder
        )

    async def process(self):
        """
        执行任务主流程
        
        1. 初始规划：Planner.plan() 生成总体规划
        2. 循环执行：Planner.dispatch() 决定每一步动作
        """
        try:
            self.logger.info(f"开始执行任务: {self.data['user_query'][:100]}...")
            
            # 第一步：生成初始规划
            await self._run_initial_plan()
            
            iteration = 0
            max_iterations = self.max_iterations
            
            # 主循环：不断执行 planner.dispatch() 返回的动作
            while iteration < max_iterations:
                iteration += 1
                self.logger.info(f"第 {iteration} 次迭代")
                
                # 调用 Dispatcher 决定下一步动作
                completion, thinking, action = await self._run_dispatcher()
                
                if not action or not action.get("type"):
                    self.logger.warning("Dispatcher 返回空动作，结束任务")
                    break
                
                action_type = action.get("type")
                params = action.get("params", {})
                
                # 处理不同的动作类型
                if action_type == "execute":
                    # 执行具体操作
                    await self._handle_execute_action(params)
                
                elif action_type == "save_info":
                    # 保存信息到记忆
                    key = params.get("key", "")
                    value = params.get("value", "")
                    self.task_memory.save_info(key, value)
                    self.logger.info(f"已保存信息: {key} = {value}")
                    
                    # 记录动作
                    self.task_memory.add_dispatcher_action(
                        "save_info",
                        {"key": key, "value": value}
                    )
                
                elif action_type == "modify_plan":
                    # 修改规划
                    new_plan = params.get("new_plan", "")
                    self.task_memory.set_plan(new_plan)
                    self.logger.info(f"规划已更新: {new_plan}")
                    
                    # 记录动作
                    self.task_memory.add_dispatcher_action(
                        "modify_plan",
                        {"new_plan": new_plan}
                    )
                
                elif action_type == "reply":
                    # 任务完成，回复用户
                    reply_message = params.get("message", "任务已完成")
                    self.logger.info(f"任务完成，回复用户: {reply_message}")
                    
                    # 记录动作
                    self.task_memory.add_dispatcher_action(
                        "reply",
                        {"message": reply_message}
                    )
                    
                    # 发送回复给用户，标记任务完成
                    intermediate_output = {
                        "message": reply_message
                    }
                    await self.send_callback("reply", intermediate_output, is_complete=True)
                    break
                
                else:
                    self.logger.warning(f"未知的动作类型: {action_type}")
                    
                time.sleep(1)  # 避免过快循环
            
            if iteration >= max_iterations:
                self.logger.warning(f"达到最大迭代次数 {max_iterations}，停止执行")
            
            self.logger.info("任务执行完成")
            
        except Exception as e:
            self.logger.error(f"任务执行失败: {e}", exc_info=True)
            raise
    
    async def _handle_execute_action(self, params: Dict):
        """处理 execute 动作"""
        action_desc = params.get("action", "")
        
        self.logger.info(f"执行动作: {action_desc}")
        
        # 调用 Executor
        await self._run_executor(action_desc)
        
        # 记录动作
        self.task_memory.add_dispatcher_action(
            "execute",
            {"action": action_desc}
        )
    
    async def _run_executor(self, action: str):
        """运行执行器"""
        loop = asyncio.get_event_loop()
        completion, actions = await loop.run_in_executor(
            None,
            partial(self.executor, action, self.task_memory)
        )
        
        self.logger.info(
            f"Executor 结果:\n"
            f"  model: {self.data['grounding_model']}\n"
            f"  action: {action}\n"
            f"  actions: {actions}"
        )
        
        intermediate_output = {
            "model": self.data["grounding_model"],
            "action": action,
            "actions": actions
        }
        await self.send_callback("executor", intermediate_output)
    
    async def _run_initial_plan(self):
        """运行初始规划"""
        loop = asyncio.get_event_loop()
        completion, thinking, plan = await loop.run_in_executor(
            None, 
            partial(self.planner.plan, self.data["user_query"])
        )
        
        # 设置初始规划
        self.task_memory.set_plan(plan)
        
        self.logger.info(
            f"初始规划结果:\n"
            f"  model: {self.data['planning_model']}\n"
            f"  thinking: {thinking}\n"
            f"  plan: {plan}"
        )
        
        intermediate_output = {
            "model": self.data["planning_model"],
            "thinking": thinking,
            "plan": plan
        }
        await self.send_callback("planner", intermediate_output)
    
    async def _run_dispatcher(self) -> tuple:
        """运行分发决策（使用 Planner.dispatch）"""
        loop = asyncio.get_event_loop()
        completion, thinking, action = await loop.run_in_executor(
            None,
            partial(self.planner.dispatch, self.task_memory, self.task_max_memory_steps)
        )
        
        self.logger.info(
            f"Planner.dispatch 结果:\n"
            f"  model: {self.data['planning_model']}\n"
            f"  thinking: {thinking}\n"
            f"  action: {action}"
        )
        
        intermediate_output = {
            "model": self.data["planning_model"],
            "thinking": thinking,
            "action": action
        }
        await self.send_callback("planner", intermediate_output)
        
        return completion, thinking, action

