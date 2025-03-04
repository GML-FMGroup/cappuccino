import base64
import json
import logging
import os
from openai import OpenAI
from .planner_utils import get_system_prompt, parse_tasks, encode_image

class text_planner:
    def __init__(self, executor_api_key, executor_base_url, executor_model, planner_api_key, planner_base_url, planner_model, controlledOS):
        self.vision_client = OpenAI(
            api_key=executor_api_key,
            base_url=executor_base_url,
        )
        self.planner_client = OpenAI(
            api_key=planner_api_key,
            base_url=planner_base_url,
        )
        self.vision_model = executor_model
        self.planner_model = planner_model
        self.controlledOS = controlledOS

    def _get_vision_system_prompt(self, controlledOS):
        return f"""
You are using a {controlledOS} system.
You will receive a desktop screenshot. Please generate a detailed description based on this screenshot, covering, but not limited to, the following aspects:

**Desktop Background**: Describe the background of the desktop, whether it has a specific theme or pattern.
**Applications and Windows**: List the applications and windows open on the desktop, including their names, functions, and any notable features.
**Icons and Shortcuts**: Describe the icons and shortcuts visible on the desktop, indicating which applications or functions they represent.
**Taskbar or Menu Bar**: Describe the elements in the taskbar or menu bar, including any visible programs, buttons, or status indicators.
**System Status**: Are there any special system notifications or prompts on the screen, such as unread messages or network connection status?
**Other Visible Elements**: Describe any other visible elements on the desktop, such as folders, open documents, or browser tabs.
**Layout and Structure**: Provide any insights on the arrangement and structure of the desktop elements, whether there are any special groupings or arrangements.

Please provide a comprehensive and detailed description, ensuring that all aspects of the current desktop are covered.
"""

    def _get_user_prompt(self, query, screenshot_description):
        return f"""
## User Query:
{query}
## Screenshot Description:
{screenshot_description}
"""

    def __call__(self, screenshot_path, query):
        base64_image = encode_image(screenshot_path)

        vision_messages=[
            {
                "role": "system",
                "content": self._get_vision_system_prompt(self.controlledOS),
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Please describe the picture as required"},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{base64_image}"},
                    },
                ],
            }
        ]
        vision_completion = self.vision_client.chat.completions.create(
            model=self.vision_model,
            messages=vision_messages
        )
        screenshot_description = vision_completion.choices[0].message.content
        logging.info(f"Screenshot description: {screenshot_description}\n\n")

        messages=[
            {
                "role": "system",
                "content": get_system_prompt(self.controlledOS),
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": self._get_user_prompt(query, screenshot_description)},
                ],
            }
        ]
        completion = self.planner_client.chat.completions.create(
            model=self.planner_model,
            messages=messages
        )
        output_text = completion.choices[0].message.content
        tasks = parse_tasks(output_text)
        return output_text, tasks