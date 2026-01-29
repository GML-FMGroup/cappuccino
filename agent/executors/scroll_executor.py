import platform
import re
import json
import pyautogui
import os
from IPython.display import display
from typing import Union
from qwen_agent.tools.base import BaseTool, register_tool
from qwen_agent.llm.fncall_prompts.nous_fncall_prompt import (
    NousFnCallPrompt,
    Message,
    ContentItem,
)


@register_tool("computer_use_scroll")
class ComputerUse(BaseTool):
    @property
    def description(self):
        return f"""
Your task is to find the required information through mouse scrolling. Please note that you can move the mouse to the place you need to scroll before scrolling.
* The system you are currently operating is {self.controlledOS}, Be careful when using the shortcut keys.
* The screen's resolution is {self.display_width_px}x{self.display_height_px}.
""".strip()

    parameters = {
        "properties": {
            "action": {
                "description": """
The action to perform. The available actions are:
* `mouse_move`: Move the cursor to a specified (x, y) pixel coordinate on the screen.
* `scroll`: Performs a scroll of the mouse scroll wheel.
""".strip(),
                "enum": [
                    "mouse_move",
                    "scroll",
                ],
                "type": "string",
            },
            "coordinate": {
                "description": "(x, y): The x (pixels from the left edge) and y (pixels from the top edge) coordinates to move the mouse to. Required only by `action=mouse_move` and `action=click`.",
                "type": "array",
            },
        },
        "required": ["action"],
        "type": "object",
    }

    def __init__(self, cfg=None):
        self.display_width_px = cfg["display_width_px"]
        self.display_height_px = cfg["display_height_px"]
        self.controlledOS = cfg["controlledOS"]
        super().__init__(cfg)

    def call(self, params: Union[str, dict], **kwargs):
        pass


class scroll_executor:
    """
    Parameters:
    - executor_client
    - executor_model (str): Model to be used by the executor client
    - base64_screenshot (str): The base64 encoded screenshot
    - subtask (str): The subtask to be executed

    Returns:
    - completion (str): The full output of LLM
    - actions (arr): The action of the executed subtask
    """
    def __init__(self, executor_client, executor_model):
        self.executor_client = executor_client
        self.executor_model = executor_model
        self.controlledOS = platform.system()

    def _parse_tool_call(self, text):
        try:
            # 使用正则表达式提取所有 <tool_call> 和 </tool_call> 之间的内容
            matches = re.findall(r'<tool_call>\n(.*?)\n</tool_call>', text, re.DOTALL)
            # 将每个匹配的字符串解析为 JSON 对象
            actions = [json.loads(match) for match in matches]
        except:
            actions = []
        return actions
    
    def gui_action(self, arguments):
        if arguments["action"] == "mouse_move":
            pyautogui.moveTo(arguments["coordinate"][0], arguments["coordinate"][1])
        elif arguments["action"] == "scroll":
            if self.controlledOS == "Windows":
                pyautogui.scroll(-500)
            elif self.controlledOS == "Darwin":
                pyautogui.scroll(-10)
            elif self.controlledOS == "Linux":
                pyautogui.scroll(-10)

    def __call__(self, base64_screenshot, subtask, min_pixels=3136, max_pixels=12845056):
        """
        Perform GUI grounding using Qwen model to interpret user query on a screenshot.
        
        Args:
            screenshot_path (str): Path to the screenshot image
            task (str): User's query/instruction
            model: Preloaded Qwen model
            min_pixels: Minimum pixels for the image
            max_pixels: Maximum pixels for the image
            
        Returns:
            tuple: (output_text, display_image) - Model's output text and annotated image
        """

        # Open and process image
        display_width_px, display_height_px = pyautogui.size()
        # Initialize computer use function
        computer_use = ComputerUse(
            cfg={"display_width_px": display_width_px, "display_height_px": display_height_px, "controlledOS": self.controlledOS}
        )
        
        # Build messages
        system_message = NousFnCallPrompt.preprocess_fncall_messages(
            messages=[
                Message(role="system", content=[ContentItem(text="You are a helpful assistant.")]),
            ],
            functions=[computer_use.function],
            lang=None,
        )
        system_message = system_message[0].model_dump()
        messages=[
            {
                "role": "system",
                "content": [
                    {"type": "text", "text": msg["text"]} for msg in system_message["content"]
                ],
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "min_pixels": min_pixels,
                        "max_pixels": max_pixels,
                        "image_url": {"url": f"data:image/png;base64,{base64_screenshot}"},
                    },
                    {"type": "text", "text": subtask},
                ],
            }
        ]

        completion = self.executor_client.chat.completions.create(
            model = self.executor_model,
            messages = messages,
        )
        actions = self._parse_tool_call(completion.choices[0].message.content)
        
        # The model cannot move the mouse to the target area very well. By default, the mouse is moved to the middle first.
        pyautogui.moveTo(display_width_px // 2, display_height_px // 2)

        for action in actions:
            self.gui_action(action['arguments'])
        
        return completion, actions
