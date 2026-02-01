"""
执行器 (Executor)
负责执行具体的电脑操控动作

- interact_executor: 使用 grounding 模型
- code_executor: 使用 planning 模型
"""

import os
import platform
import time
import json
from typing import Dict, Tuple, List, Optional

from openai import OpenAI
from .utils import get_base64_screenshot
from .executors import *
from .memory import TaskContextMemory


class Executor:
    """
    执行器管理器
    
    根据子任务类型选择合适的执行器和模型
    
    - interact_executor, scroll_executor: 使用 grounding 模型（视觉定位）
    - code_executor: 使用 planning 模型（文本理解）
    """
    
    def __init__(
        self, 
        planning_config: Dict, 
        grounding_config: Dict, 
        run_folder: str
    ):
        """
        初始化执行器
        
        Args:
            planning_config: Planning 模型配置 {"api_key", "base_url", "model"}
            grounding_config: Grounding 模型配置 {"api_key", "base_url", "model"}
            run_folder: 运行目录
        """
        # Planning 模型客户端 (用于 ocr, code)
        self.planning_client = OpenAI(
            api_key=planning_config["api_key"],
            base_url=planning_config["base_url"],
        )
        self.planning_model = planning_config["model"]
        
        # Grounding 模型客户端 (用于 interact, scroll)
        self.grounding_client = OpenAI(
            api_key=grounding_config["api_key"],
            base_url=grounding_config["base_url"],
        )
        self.grounding_model = grounding_config["model"]
        
        self.controlled_os = platform.system()
        self.run_folder = run_folder
        os.environ["RUN_FOLDER"] = run_folder

    def __call__(
        self, 
        action_dict: Dict, 
        task_memory: Optional[TaskContextMemory] = None
    ) -> Tuple[str, List]:
        """
        执行子任务
        
        Args:
            action_dict: 动作字典 {"executor": "...", "action": "..."}
            task_memory: 任务上下文记忆
        
        Returns:
            (LLM 响应, 执行动作列表)
        """
        executor_type = action_dict.get('executor', '')
        action = action_dict.get('action', '')
        
        # 获取当前屏幕截图
        base64_screenshot = get_base64_screenshot(self.run_folder)
        
        completion = "No matching executor"
        actions = []

        if executor_type == 'wait':
            # 等待操作
            time.sleep(0.5)
            completion = "Wait completed"
            actions = [{"name": "wait", "arguments": "0.5 seconds"}]
        
        elif executor_type == 'interact_executor':
            # 使用 grounding 模型进行交互操作
            action_executor = interact_executor(
                self.grounding_client, 
                self.grounding_model
            )
            completion, actions = action_executor(base64_screenshot, action)

        elif executor_type == 'code_executor':
            # 使用 planning 模型生成并执行代码
            action_executor = code_executor(
                self.planning_client, 
                self.planning_model
            )
            completion, actions = action_executor(action)
        
        else:
            completion = f"Unknown executor: {executor_type}"
            actions = []
        
        return completion, actions


# 兼容旧的类名（小写）
executor = Executor

