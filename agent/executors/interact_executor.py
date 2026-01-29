import os
import platform
import re
import json
import time
import pyperclip
import pyautogui
from IPython.display import display
from typing import Union
from qwen_agent.tools.base import BaseTool, register_tool
from qwen_agent.llm.fncall_prompts.nous_fncall_prompt import (
    NousFnCallPrompt,
    Message,
    ContentItem,
)


@register_tool("computer_use")
class ComputerUse(BaseTool):
    @property
    def description(self):
        return f"""
Use a mouse and keyboard to interact with a computer, and take screenshots.
* This is an interface to a desktop GUI. You do not have access to a terminal or applications menu. You must click on desktop icons to start applications.
* Some applications may take time to start or process actions, so you may need to wait and take successive screenshots to see the results of your actions. E.g. if you click on Firefox and a window doesn't open, try wait and taking another screenshot.
* The system you are currently operating is {self.controlledOS}, Be careful when using the shortcut keys.
* The screen's resolution is {self.display_width_px}x{self.display_height_px}.
* Whenever you intend to move the cursor to click on an element like an icon, you should consult a screenshot to determine the coordinates of the element before moving the cursor.
* If you tried clicking on a program or link but it failed to load, even after waiting, try adjusting your cursor position so that the tip of the cursor visually falls on the element that you want to click.
* Make sure to click any buttons, links, icons, etc with the cursor tip in the center of the element. Don't click boxes on their edges unless asked.
""".strip()

    parameters = {
        "properties": {
            "action": {
                "description": """
The action to perform. The available actions are:
* `key`: Performs key down presses on the arguments passed in order, then performs key releases in reverse order.
* `type`: Type a string of text on the keyboard.
* `mouse_move`: Move the cursor to a specified (x, y) pixel coordinate on the screen.
* `left_click`: Click the left mouse button.
* `right_click`: Click the right mouse button.
* `middle_click`: Click the middle mouse button.
* `double_click`: Double-click the left mouse button.
""".strip(),
                "enum": [
                    "key",
                    "type",
                    "mouse_move",
                    "left_click",
                    "right_click",
                    "middle_click",
                    "double_click",
                ],
                "type": "string",
            },
            "keys": {
                "description": "Required only by `action=key`.",
                "type": "array",
            },
            "text": {
                "description": "Required only by `action=type`.",
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


class interact_executor:
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
    
    def _gui_action(self, arguments):
        if arguments["action"] == "key":
            if len(arguments["keys"]) == 1:
                pyautogui.typewrite(arguments["keys"])
            else:
                for key in arguments["keys"][:-1]:
                    pyautogui.keyDown(key)
                pyautogui.press(arguments["keys"][-1])
                for key in reversed(arguments["keys"][:-1]):
                    pyautogui.keyUp(key)
        elif arguments["action"] == "type":
            pyperclip.copy(arguments["text"])
            time.sleep(0.1)
            if self.controlledOS == "Darwin":
                pyautogui.keyDown('command')
                pyautogui.press('v')
                pyautogui.keyUp('command')
            else:
                pyautogui.keyDown('ctrl')
                pyautogui.press('v')
                pyautogui.keyUp('ctrl')
        elif arguments["action"] == "mouse_move":
            pyautogui.moveTo(arguments["coordinate"][0], arguments["coordinate"][1])
        elif arguments["action"] == "left_click":
            pyautogui.doubleClick(arguments["coordinate"][0], arguments["coordinate"][1])
        elif arguments["action"] == "right_click":
            pyautogui.rightClick(arguments["coordinate"][0], arguments["coordinate"][1])
        elif arguments["action"] == "middle_click":
            pyautogui.middleClick(arguments["coordinate"][0], arguments["coordinate"][1])
        elif arguments["action"] == "double_click":
            pyautogui.doubleClick(arguments["coordinate"][0], arguments["coordinate"][1])

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
        
        for action in actions:
            self._gui_action(action['arguments'])
        
        return completion, actions
