import json
import os
import platform
import logging
import time
from .utils import get_base64_screenshot
from .planner import planner
from .dispatcher import dispatcher
from .executor import executor
from .verifier import verifier

class Agent:
    """
    Parameters:
    - send_callback (function: (role, intermediate_output)): function to send callback with role and intermediate_output
    - data (obj): dictionary containing the following keys:
        - planner_model(str)
        - planner_api_key(str)
        - planner_base_url(str)
        - dispatcher_model(str)
        - dispatcher_api_key(str)
        - dispatcher_base_url(str)
        - executor_model(str)
        - executor_api_key(str)
        - executor_base_url(str)
        - user_query(str)
    """

    def __init__(self, send_callback, data):
        self.send_callback = send_callback
        self.data = data

        # Initialize controlledOS and run_folder as environment variables
        self.controlledOS = platform.system()
        self.run_folder = os.path.join('temp', time.strftime("%Y%m%d-%H%M%S"))
        os.makedirs(self.run_folder, exist_ok=True)
        os.environ["RUN_FOLDER"] = self.run_folder

        self.logger = logging.getLogger(f"AgentLogger-{self.controlledOS}")
        self.logger.setLevel(logging.DEBUG)  # 设置日志级别为 DEBUG
        file_handler = logging.FileHandler(os.path.join(self.run_folder, 'agent.log'))
        file_handler.setLevel(logging.DEBUG)  # 确保处理器的日志级别也为 DEBUG
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(file_handler)
        self.logger.propagate = False  # 防止日志传播到根记录器

        # 测试日志记录器是否正常工作
        self.logger.debug("Logger initialized successfully.")

        with open(os.path.join(self.run_folder, 'memory.json'), 'w') as memory_file:
            json.dump({"tasks": [], "data": []}, memory_file, indent=4)

        self.planner = planner(
            self.data["planner_api_key"],
            self.data["planner_base_url"],
            self.data["planner_model"]
        )

        self.dispatcher = dispatcher(
            self.data["dispatcher_api_key"],
            self.data["dispatcher_base_url"],
            self.data["dispatcher_model"]
        )

        self.executor = executor(
            self.data["executor_api_key"],
            self.data["executor_base_url"],
            self.data["executor_model"]
        )

        self.verifier = verifier(
            self.data["dispatcher_api_key"],
            self.data["dispatcher_base_url"],
            self.data["dispatcher_model"]
        )


    async def process(self):
        try:
            tasks = await self.pipeline_planner(self.data["user_query"])
            for task in tasks:
                is_completed = False
                completed_retry_count = 0
                while not is_completed and completed_retry_count < 3:
                    subtasks = await self.pipeline_dispatcher(task)
                    # Handle special executors that might need retries
                    retry_configs = {
                        "wait": {"max_retries": 2, "message": "Handling page load delay"},
                        "scroll_executor": {"max_retries": 8, "message": "Scrolling to find target content"}
                    }
                    if subtasks[0]["executor"] in retry_configs:
                        config = retry_configs[subtasks[0]["executor"]]
                        self.logger.debug(f"{config['message']}\n")
                        for retry in range(config["max_retries"]):
                            await self.pipeline_executor(subtasks[0])
                            subtasks = await self.pipeline_dispatcher(task)
                            if subtasks[0]["executor"] not in retry_configs:
                                 break

                    for subtask_dict in subtasks:
                        await self.pipeline_executor(subtask_dict)
                        
                    time.sleep(0.5)

                    # Check whether the current task has been completed
                    is_completed = await self.pipeline_verifier(task)
                    completed_retry_count += 1

        except Exception as e:
            self.logger.error("Error in process method", exc_info=True)
            raise


    async def pipeline_planner(self, query):
        # tasks example: ["task", "task"]
        completion, thinking, tasks = self.planner(query)
        self.logger.info(f"planner_model: {self.data['planner_model']}\nquery: {query}\ncompletion: {completion}\nthinking: {thinking}\ntasks:{tasks}\n\n")
        intermediate_output = {
            "planner_model": self.data["planner_model"],
            "query": query,
            "thinking": thinking,
            "tasks": tasks
        }
        await self.send_callback("planner", intermediate_output)
        return tasks
    
    async def pipeline_dispatcher(self, task):
        # subtasks example: [{executor: "", subtask: ""}, {executor: "", subtask: ""}]
        completion, thinking, subtasks = self.dispatcher(task)
        self.logger.info(f"dispatcher_model: {self.data['dispatcher_model']}\ntask: {task}\ncompletion: {completion}\nthinking: {thinking}\nsubtasks:{subtasks}\n\n")
        intermediate_output = {
            "dispatcher_model": self.data["dispatcher_model"],
            "task": task,
            "thinking": thinking,
            "subtasks": subtasks
        }
        await self.send_callback("dispatcher", intermediate_output)
        return subtasks

    async def pipeline_executor(self, subtask):
        completion, actions = self.executor(subtask)
        self.logger.info(f"executor_model: {self.data['executor_model']}\nsubtask: {subtask}\ncompletion: {completion}\nactions: {actions}\n\n")
        intermediate_output = {
            "executor_model": self.data["executor_model"],
            "subtask": subtask,
            "actions": actions
        }
        await self.send_callback("executor", intermediate_output)

    async def pipeline_verifier(self, task):
        completion, thinking, is_completed = self.verifier(task)
        self.logger.info(f"verifier_model: {self.data['dispatcher_model']}\ntask: {task}\ncompletion: {completion}\nthinking: {thinking}\nis_completed:{is_completed}\n\n")
        intermediate_output = {
            "verifier_model": self.data["dispatcher_model"],
            "task": task,
            "thinking": thinking,
            "is_completed": is_completed
        }
        await self.send_callback("verifier", intermediate_output)
        return is_completed

