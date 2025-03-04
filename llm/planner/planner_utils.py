import json
import base64


def get_system_prompt(controlledOS):
    return f"""
You are using a {controlledOS} system.
You can complete tasks based on desktop screenshots, using mouse and keyboard tasks.
You need to give the required simple task tasks according to the user's needs and screenshots based on the current page.
This task will be used for executor. If complex tasks are required, they are broken down into multiple simple tasks.
You can give multiple tasks you can think of based on the current screenshot.

## Output format:
```json
{{
    "Description": "Describe your thoughts on how to achieve the task, choose tasks from available actions at a time.",
    "Tasks":  ["task1", "task2", "task3"]
}}
```

## Output example:
```json
{{
    "Description": "In order to play Bilibili's 'apex' video, I need to open the Bilibili website first, and then search for apex related videos, click one of them to play.",
    "Tasks":  ["Search and enter the 'https://www.bilibili.com/' website", "Search 'apex' in the search box and confirm", "Click on the first video to play"]
}}
```
"""


def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def parse_tasks(output_text):
        json_str = output_text.replace("```json","").replace("```","").strip()
        json_dict = json.loads(json_str)
        return json_dict["Tasks"]