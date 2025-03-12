import os
import platform
import logging
import time
from computer.screen_capture import capture_screen
from llm.planner.text_planner import text_planner
from llm.planner.multimodal_planner import multimodal_planner
from llm.executor.Qwen2_5_VL_executor import Qwen2_5_VL_executor
from computer.gui_action import GuiAction

TEXT_MODEL = ["deepseek-v3"]

class Agent:
    def __init__(self, send_callback, data):

        self.send_callback = send_callback
        self.data = data
        # 系统类型：Darwin(Macos), Windows, Linux
        self.controlledOS = platform.system()
        self.gui_action = GuiAction(self.controlledOS)

        # 创建日志文件夹
        if not os.path.exists('temp'):
            os.makedirs('temp')
        # 配置 logging 基础设置
        logging.basicConfig(
            level=logging.INFO,  # 设置日志级别为 INFO
            format='%(asctime)s - %(levelname)s - %(message)s',  # 日志格式
            handlers=[
                logging.FileHandler(os.path.join('temp', 'agent.log')),  # 输出到文件
                # logging.StreamHandler()  # 输出到控制台
            ]
        )

        # 初始化planner和executor
        if self.data["agent_type"] == 'planner':
            if self.data["planner_model"] in TEXT_MODEL:
                self.planner = text_planner(
                    self.data["executor_api_key"],
                    self.data["executor_base_url"],
                    self.data["executor_model"],
                    self.data["planner_api_key"],
                    self.data["planner_base_url"],
                    self.data["planner_model"],
                    self.controlledOS
                )
            else:
                self.planner = multimodal_planner(
                    self.data["planner_api_key"],
                    self.data["planner_base_url"],
                    self.data["planner_model"],
                    self.controlledOS
                )
        self.executor = Qwen2_5_VL_executor(
            self.data["executor_api_key"],
            self.data["executor_base_url"],
            self.data["executor_model"],
            self.controlledOS,
        )


    async def process(self):
        # 如果是planner模式，需要先生成任务流再执行，让planner model判断是否完成指定任务
        if self.data["agent_type"] == 'planner':
            planner_output_text, tasks = await self.pipeline_planner(self.data["user_query"])
            executor_output_text = await self.pipeline_executor(tasks)

        # 如果是workflow模式，直接执行任务流
        elif self.data["agent_type"] == 'workflow':
            executor_output_text = await self.pipeline_executor(self.data["user_tasks"])


    async def pipeline_planner(self, query):
        # 使用planner生成任务流，若planner model为text_planner，则使用executor model作为vision model
        # 任务流tasks格式：[task1, task2, task3, ...]
        # 获取屏幕截图并获取截图路径
        screenshot_path = capture_screen()
        output_text, description, tasks = self.planner(
            screenshot_path,
            query,
        )
        logging.info(f"planner_model: {self.data['planner_model']}\nquery: {query}\noutput_text: {output_text}\n\n")
        intermediate_output = {
            "query": query,
            "description": description,
            "tasks": tasks
        }
        await self.send_callback("planner", intermediate_output)
        return output_text, tasks

    async def pipeline_executor(self, tasks):
        # 使用executor逐步执行任务流
        # action参数示例：
        # arguments: {"action": "left_click", "coordinate": [230, 598]}
        # arguments: {"action": "type", "text": "英雄联盟"}
        # arguments: {"action": "key", "keys": ["enter"]}
        for task in tasks:
            # 获取屏幕截图并获取截图路径
            screenshot_path = capture_screen()
            # 调用executor生成并执行动作
            output_text, actions = self.executor(
                screenshot_path, 
                task
            )
            # 逐个执行动作
            for action in actions:
                self.gui_action(action["arguments"])
                time.sleep(0.5)

            logging.info(f"executor_model: {self.data['executor_model']}\ntask: {task}\noutput_text: {output_text}\n\n")
            intermediate_output = {
                "task": task,
                "actions": actions
            }
            await self.send_callback("executor", intermediate_output)
            time.sleep(1)

                
        return output_text
