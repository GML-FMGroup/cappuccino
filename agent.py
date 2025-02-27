import os
import platform
import logging
from openai import OpenAI
from computer.screen_capture import capture_screen
from llm.planner.QwenVL_planner import QwenVL_planner
from llm.executor.Qwen2_5_VL_executor import Qwen2_5_VL_executor


class Agent:
    def __init__(self, send_callback, data):

        self.send_callback = send_callback
        self.data = data
        
        # 创建日志文件夹
        if not os.path.exists('temp'):
            os.makedirs('temp')
        # 配置 logging 基础设置
        logging.basicConfig(
            level=logging.INFO,  # 设置日志级别为 INFO
            format='%(asctime)s - %(levelname)s - %(message)s',  # 日志格式
            handlers=[
                logging.FileHandler(os.path.join('temp', 'agent.log')),  # 输出到文件
                logging.StreamHandler()  # 输出到控制台
            ]
        )

        # 系统类型：Darwin(Macos), Windows, Linux
        self.controlledOS = platform.system()

        # 初始化planner和executor
        if self.data["agent_type"] == 'planner':
            self.planner = QwenVL_planner(
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
        self.history = []


    async def process(self):

        # 如果是planner模式，需要先生成任务流再执行，让planner model判断是否完成指定任务
        # 任务流tasks格式：[task1, task2, task3, ...]
        if self.data["agent_type"] == 'planner':

            planner_output_text, tasks = await self.pipeline_planner(self.data["user_query"])
            executor_output_text = await self.pipeline_executor(tasks)

        # 如果是workflow模式，直接执行任务流
        elif self.data["agent_type"] == 'workflow':
            executor_output_text = await self.pipeline_executor(self.data["user_tasks"])


    async def pipeline_planner(self, query):
        # 使用planner生成任务流
        # 获取屏幕截图并获取截图路径
        screenshot_path = capture_screen()
        output_text, tasks = self.planner.perform_planning(
            screenshot_path,
            query,
            self.history
        )
        self.history.append(output_text)
        logging.info(f"planner_model: {self.data['planner_model']}\nquery: {query}\noutput_text: {output_text}\n\n")
        await self.send_callback(f"planner_output: {output_text}")
        return output_text, tasks

    async def pipeline_executor(self, tasks):
        # 逐步执行任务流
        for task in tasks:
            # 获取屏幕截图并获取截图路径
            screenshot_path = capture_screen()
            # 调用executor生成并执行动作
            output_text = self.executor.perform_executor(
                screenshot_path, 
                task
            )
            logging.info(f"executor_model: {self.data['executor_model']}\ntask: {task}\noutput_text: {output_text}\n\n")
            await self.send_callback(f"task: {task} executor_output: {output_text}", is_send_image=True)
                
        return output_text
