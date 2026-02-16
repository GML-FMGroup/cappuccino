"""
执行器 (Executor)
负责执行具体的电脑操控动作（鼠标点击、键盘输入、等待、滚动等）
"""

import base64
import io
import json
import math
import os
import platform
import time
from typing import Any, Dict, Tuple, List, Optional, Union

import pyautogui
import pyperclip
from PIL import Image
from openai import OpenAI
from qwen_agent.llm.fncall_prompts.nous_fncall_prompt import (
    ContentItem,
    Message,
    NousFnCallPrompt,
)
from qwen_agent.tools.base import BaseTool, register_tool

from .utils import get_base64_screenshot
from .memory import TaskContextMemory


def smart_resize(
    height: int,
    width: int,
    factor: int = 32,
    min_pixels: int = 3136,
    max_pixels: int = 12845056,
) -> tuple[int, int]:
    if height <= 0 or width <= 0:
        return factor, factor

    area = height * width
    target_area = area
    if area < min_pixels:
        target_area = min_pixels
    elif area > max_pixels:
        target_area = max_pixels

    scale = math.sqrt(target_area / area)
    new_height = max(factor, int(round(height * scale / factor) * factor))
    new_width = max(factor, int(round(width * scale / factor) * factor))
    return new_height, new_width


@register_tool("computer_use")
class ComputerUse(BaseTool):
    @property
    def description(self):
        return f"""
Use a mouse and keyboard to interact with a computer, and take screenshots.
* This is an interface to a desktop GUI. You do not have access to a terminal or applications menu. You must click on desktop icons to start applications.
* Some applications may take time to start or process actions, so you may need to wait and take successive screenshots to see the results of your actions. E.g. if you click on Firefox and a window doesn't open, try wait and taking another screenshot.
* The screen's resolution is {self.display_width_px}x{self.display_height_px}.
* Whenever you intend to move the cursor to click on an element like an icon, you should consult a screenshot to determine the coordinates of the element before moving the cursor.
* If you tried clicking on a program or link but it failed to load, even after waiting, try adjusting your cursor position so that the tip of the cursor visually falls on the element that you want to click.
* Make sure to click any buttons, links, icons, etc with the cursor tip in the center of the element. Don't click boxes on their edges.
""".strip()

    parameters = {
        "properties": {
            "action": {
                "description": """
The action to perform. The available actions are:
* `key`: Performs key down presses on the arguments passed in order, then performs key releases in reverse order.
* `type`: Type a string of text on the keyboard.
* `mouse_move`: Move the cursor to a specified (x, y) pixel coordinate on the screen.
* `left_click`: Click the left mouse button at a specified (x, y) pixel coordinate on the screen.
* `left_click_drag`: Click and drag the cursor to a specified (x, y) pixel coordinate on the screen.
* `right_click`: Click the right mouse button at a specified (x, y) pixel coordinate on the screen.
* `middle_click`: Click the middle mouse button at a specified (x, y) pixel coordinate on the screen.
* `double_click`: Double-click the left mouse button at a specified (x, y) pixel coordinate on the screen.
* `triple_click`: Triple-click the left mouse button at a specified (x, y) pixel coordinate on the screen (simulated as double-click since it's the closest action).
* `scroll`: Performs a scroll of the mouse scroll wheel.
* `hscroll`: Performs a horizontal scroll (mapped to regular scroll).
* `wait`: Wait specified seconds for the change to happen.
* `terminate`: Terminate the current task and report its completion status.
* `answer`: Answer a question.
""".strip(),
                "enum": [
                    "key",
                    "type",
                    "mouse_move",
                    "left_click",
                    "left_click_drag",
                    "right_click",
                    "middle_click",
                    "double_click",
                    "triple_click",
                    "scroll",
                    "hscroll",
                    "wait",
                    "terminate",
                    "answer",
                ],
                "type": "string",
            },
            "keys": {
                "description": "Required only by `action=key`.",
                "type": "array",
            },
            "text": {
                "description": "Required only by `action=type` and `action=answer`.",
                "type": "string",
            },
            "coordinate": {
                "description": "(x, y): The x (pixels from the left edge) and y (pixels from the top edge) coordinates to move the mouse to.",
                "type": "array",
            },
            "pixels": {
                "description": "The amount of scrolling to perform. Positive values scroll up, negative values scroll down. Required only by `action=scroll` and `action=hscroll`.",
                "type": "number",
            },
            "time": {
                "description": "The seconds to wait. Required only by `action=wait`.",
                "type": "number",
            },
            "status": {
                "description": "The status of the task. Required only by `action=terminate`.",
                "type": "string",
                "enum": ["success", "failure"],
            },
        },
        "required": ["action"],
        "type": "object",
    }

    def __init__(self, cfg=None):
        self.display_width_px = cfg["display_width_px"]
        self.display_height_px = cfg["display_height_px"]
        super().__init__(cfg)

    def call(self, params: Union[str, dict], **kwargs):
        params = self._verify_json_format_args(params)
        action = params["action"]
        if action in ["left_click", "right_click", "middle_click", "double_click","triple_click"]:
            return self._mouse_click(action)
        elif action == "key":
            return self._key(params["keys"])
        elif action == "type":
            return self._type(params["text"])
        elif action == "mouse_move":
            return self._mouse_move(params["coordinate"])
        elif action == "left_click_drag":
            return self._left_click_drag(params["coordinate"])
        elif action == "scroll":
            return self._scroll(params["pixels"])
        elif action == "hscroll":
            return self._hscroll(params["pixels"])
        elif action == "answer":
            return self._answer(params["text"])
        elif action == "wait":
            return self._wait(params["time"])
        elif action == "terminate":
            return self._terminate(params["status"])
        else:
            raise ValueError(f"Invalid action: {action}")

    def _mouse_click(self, button: str):
        raise NotImplementedError()

    def _key(self, keys: List[str]):
        raise NotImplementedError()

    def _type(self, text: str):
        raise NotImplementedError()

    def _mouse_move(self, coordinate: Tuple[int, int]):
        raise NotImplementedError()

    def _left_click_drag(self, coordinate: Tuple[int, int]):
        raise NotImplementedError()

    def _scroll(self, pixels: int):
        raise NotImplementedError()

    def _hscroll(self, pixels: int):
        raise NotImplementedError()

    def _answer(self, text: str):
        raise NotImplementedError()

    def _wait(self, time: int):
        raise NotImplementedError()

    def _terminate(self, status: str):
        raise NotImplementedError()


class Executor:
    """
    执行器管理器
    
    负责执行具体的电脑操控动作（鼠标点击、键盘输入、等待、滚动等）
    使用 grounding 模型进行视觉定位
    """
    
    def __init__(self, grounding_config: Dict, run_folder: str):
        """
        初始化执行器
        
        Args:
            grounding_config: Grounding 模型配置 {"api_key", "base_url", "model"}
            run_folder: 运行目录
        """
        self.grounding_client = OpenAI(
            api_key=grounding_config["api_key"],
            base_url=grounding_config["base_url"],
        )
        self.grounding_model = grounding_config["model"]
        
        self.controlled_os = platform.system()
        self.run_folder = run_folder
        os.environ["RUN_FOLDER"] = run_folder
        
        self.original_width = None
        self.original_height = None

    def _normalize_key(self, key: str) -> str:
        if self.controlled_os == "Darwin" and key == "cmd":
            return "command"
        return key

    def _gui_action(self, arguments: Dict[str, Any]) -> None:
        action = arguments.get("action")

        if action == "key":
            keys = arguments.get("keys", [])
            keys = [self._normalize_key(key) for key in keys]
            if len(keys) == 1:
                pyautogui.press(keys[0])
            else:
                for key in keys[:-1]:
                    pyautogui.keyDown(key)
                pyautogui.press(keys[-1])
                for key in reversed(keys[:-1]):
                    pyautogui.keyUp(key)

        elif action == "type":
            text = arguments.get("text", "")
            pyperclip.copy(text)
            time.sleep(0.1)
            if self.controlled_os == "Darwin":
                pyautogui.keyDown("command")
                pyautogui.press("v")
                pyautogui.keyUp("command")
            else:
                pyautogui.keyDown("ctrl")
                pyautogui.press("v")
                pyautogui.keyUp("ctrl")

        elif action == "mouse_move":
            coordinate = self._convert_coordinate(arguments.get("coordinate", [0, 0]))
            pyautogui.moveTo(coordinate[0], coordinate[1])
            if self.controlled_os == "Windows":
                pyautogui.scroll(-500)
            elif self.controlled_os == "Darwin":
                pyautogui.scroll(-10)
            elif self.controlled_os == "Linux":
                pyautogui.scroll(-10)

        elif action == "left_click":
            coordinate = self._convert_coordinate(arguments.get("coordinate", [0, 0]))
            pyautogui.click(coordinate[0], coordinate[1])

        elif action == "left_click_drag":
            coordinate = self._convert_coordinate(arguments.get("coordinate", [0, 0]))
            pyautogui.drag(coordinate[0], coordinate[1], duration=0.5)

        elif action == "right_click":
            coordinate = self._convert_coordinate(arguments.get("coordinate", [0, 0]))
            pyautogui.rightClick(coordinate[0], coordinate[1])

        elif action == "middle_click":
            coordinate = self._convert_coordinate(arguments.get("coordinate", [0, 0]))
            pyautogui.middleClick(coordinate[0], coordinate[1])

        elif action == "double_click":
            coordinate = self._convert_coordinate(arguments.get("coordinate", [0, 0]))
            pyautogui.doubleClick(coordinate[0], coordinate[1])

        elif action == "triple_click":
            coordinate = self._convert_coordinate(arguments.get("coordinate", [0, 0]))
            pyautogui.doubleClick(coordinate[0], coordinate[1])

        elif action == "scroll":
            if self.controlled_os == "Windows":
                pyautogui.scroll(-500)
            elif self.controlled_os == "Darwin":
                pyautogui.scroll(-10)
            elif self.controlled_os == "Linux":
                pyautogui.scroll(-10)

        elif action == "hscroll":
            if self.controlled_os == "Windows":
                pyautogui.scroll(500)
            elif self.controlled_os == "Darwin":
                pyautogui.scroll(10)
            elif self.controlled_os == "Linux":
                pyautogui.scroll(10)

        elif action == "wait":
            wait_time = arguments.get("time", 1)
            time.sleep(wait_time)

    def _convert_coordinate(self, relative_coordinate: List[float]) -> List[float]:
        if not self.original_width or not self.original_height:
            return relative_coordinate
        
        absolute_x = relative_coordinate[0] / 1000.0 * self.original_width
        absolute_y = relative_coordinate[1] / 1000.0 * self.original_height
        
        return [absolute_x, absolute_y]

    def _execute_action(
        self,
        base64_screenshot: str,
        action: str,
        min_pixels: int = 3136,
        max_pixels: int = 12845056,
    ) -> Tuple[str, List]:
        if base64_screenshot.startswith("data:"):
            base64_screenshot = base64_screenshot.split("base64,", 1)[-1]

        input_image = Image.open(io.BytesIO(base64.b64decode(base64_screenshot)))
        
        self.original_width = input_image.width
        self.original_height = input_image.height

        computer_use = ComputerUse(cfg={"display_width_px": 1000, "display_height_px": 1000})

        system_message = NousFnCallPrompt().preprocess_fncall_messages(
            messages=[
                Message(role="system", content=[ContentItem(text="You are a helpful assistant.")]),
            ],
            functions=[computer_use.function],
            lang=None,
        )
        system_message = system_message[0].model_dump()
        messages = [
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
                        "image_url": {"url": f"data:image/png;base64,{base64_screenshot}"},
                    },
                    {"type": "text", "text": action},
                ],
            },
        ]

        completion = self.grounding_client.chat.completions.create(
            model=self.grounding_model,
            messages=messages,
        )

        output_text = completion.choices[0].message.content or ""

        action_result: Optional[Dict[str, Any]] = None
        if "<tool_call>" in output_text:
            tool_payload = output_text.split("<tool_call>\n", 1)[1].split("\n</tool_call>", 1)[
                0
            ]
            action_result = json.loads(tool_payload)
        else:
            try:
                action_result = json.loads(output_text)
            except json.JSONDecodeError:
                action_result = None

        actions: List[Dict[str, Any]] = []
        if action_result:
            actions.append(action_result)
            arguments = action_result.get("arguments", {})
            self._gui_action(arguments)

        return completion, actions

    def __call__(
        self, 
        action: str, 
        task_memory: Optional[TaskContextMemory] = None
    ) -> Tuple[str, List]:
        """
        执行动作
        
        Args:
            action: 动作描述 (如 "点击搜索按钮", "等待页面加载")
            task_memory: 任务上下文记忆
        
        Returns:
            (LLM 响应, 执行动作列表)
        """
        base64_screenshot = get_base64_screenshot(self.run_folder)
        return self._execute_action(base64_screenshot, action)


executor = Executor
