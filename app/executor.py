import os
import time
import json
from utils import get_base64_screenshot
from openai import OpenAI
from executors import interact_executor, scroll_executor, ocr_executor

class executor:
    """
    Parameters:
    - executor_api_key (str): API key for the executor client
    - executor_base_url (str): Base URL for the executor client
    - executor_model (str): Model to be used by the executor client
    - controlledOS (str): The operating system being controlled
    - run_folder (str): The folder to store the run data
    - base64_screenshot (str): The base64 encoded screenshot
    - subtask (str): The subtask to be executed

    Returns:
    - completion (str): The full output of LLM
    - actions (arr): The action of the executed subtask
    """
    def __init__(self, executor_api_key, executor_base_url, executor_model):
        self.executor_client = OpenAI(
            api_key=executor_api_key,
            base_url=executor_base_url,
        )
        self.executor_model = executor_model
        self.controlledOS = os.environ["CONTROLLED_OS"]
        self.run_folder = os.environ["RUN_FOLDER"]

    def __call__(self, subtask_dict):
        base64_screenshot = get_base64_screenshot(self.run_folder)
        completion = "No matching executor"
        actions = []

        if subtask_dict['executor'] == 'wait':
            time.sleep(0.5) 
            completion = "LLM not used"
            actions = ["wait 0.5 seconds"]
        
        elif subtask_dict['executor'] == 'interact_executor':
            action_executor = interact_executor(self.executor_client, self.executor_model)
            completion, actions = action_executor(base64_screenshot, subtask_dict['subtask'])
            
        elif subtask_dict['executor'] == 'scroll_executor':
            action_executor = scroll_executor(self.executor_client, self.executor_model)
            completion, actions = action_executor(base64_screenshot, subtask_dict['subtask'])
                    
        elif subtask_dict['executor'] == 'ocr_executor':
            action_executor = ocr_executor(self.executor_client, self.executor_model)
            completion, actions = action_executor(base64_screenshot, subtask_dict['subtask'])
            if len(actions) > 2:
                self._write_to_memory(actions[2])
        
        return completion, actions

    def _write_to_memory(self, content):
        memory_file_path = os.path.join(self.run_folder, 'memory.json')
        with open(memory_file_path, 'r') as memory_file:
            memory_content = json.load(memory_file)

        if "data" not in memory_content:
            memory_content["data"] = []

        memory_content["data"].append(content)

        with open(memory_file_path, 'w') as memory_file:
            json.dump(memory_content, memory_file, ensure_ascii=False, indent=4)

