import os
import base64
import json
import re
from openai import OpenAI

class general_planner:
    def __init__(self, planner_api_key, planner_base_url, planner_model, controlledOS):
        self.planner_client = OpenAI(
            api_key=planner_api_key,
            base_url=planner_base_url,
        )
        self.planner_model = planner_model
        self.controlledOS = controlledOS

    def _get_system_prompt(self):
        return f"""
You are using a {self.controlledOS} system.
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
    "Tasks":  ["Type 'https://www.bilibili.com/' in the search box and confirm", "search 'apex' in the search box and confirm", "Click on the first video to play"]
}}
```
"""

    def encode_image(self, image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    def _parse_tasks(self, output_text):
        json_str = output_text.replace("```json","").replace("```","").strip()
        json_dict = json.loads(json_str)
        return json_dict["Tasks"]

    def perform_planning(self, screenshot_path, query, history, min_pixels=3136, max_pixels=12845056):
        base64_image = self.encode_image(screenshot_path)

        messages=[
            {
                "role": "system",
                "content": self._get_system_prompt(),
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": query},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{base64_image}"},
                    },
                ],
            }
        ]
        completion = self.planner_client.chat.completions.create(
            model=self.planner_model,
            messages=messages
        )
        output_text = completion.choices[0].message.content
        tasks = self._parse_tasks(output_text)
        return output_text, tasks