import base64
import io
import json
import math
import platform
import time
from typing import Any, Dict, Union, Tuple, List, Optional

import pyautogui
import pyperclip
from PIL import Image
from qwen_agent.llm.fncall_prompts.nous_fncall_prompt import (
    ContentItem,
    Message,
    NousFnCallPrompt,
)
from qwen_agent.tools.base import BaseTool, register_tool


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


class interact_executor:
    """
    Parameters:
    - executor_client
    - executor_model (str): Model to be used by the executor client
    - base64_screenshot (str): The base64 encoded screenshot
    - action (str): The action to be executed

    Returns:
    - completion (str): The full output of LLM
    - actions (arr): The action of the executed task
    """

    def __init__(self, executor_client, executor_model):
        self.executor_client = executor_client
        self.executor_model = executor_model
        self.controlledOS = platform.system()
        self.original_width = None
        self.original_height = None

    def _normalize_key(self, key: str) -> str:
        """Normalize key names for pyautogui"""
        # Convert 'cmd' to 'command' for macOS
        if self.controlledOS == "Darwin" and key == "cmd":
            return "command"
        return key

    def _gui_action(self, arguments: Dict[str, Any]) -> None:
        action = arguments.get("action")

        if action == "key":
            keys = arguments.get("keys", [])
            # Normalize all keys
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
            if self.controlledOS == "Darwin":
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
            # 模拟三击为双击
            coordinate = self._convert_coordinate(arguments.get("coordinate", [0, 0]))
            pyautogui.doubleClick(coordinate[0], coordinate[1])

        elif action == "scroll":
            pixels = arguments.get("pixels", 0)
            pyautogui.scroll(pixels)

        elif action == "hscroll":
            pixels = arguments.get("pixels", 0)
            pyautogui.scroll(pixels)

        elif action == "wait":
            wait_time = arguments.get("time", 1)
            time.sleep(wait_time)

    def _convert_coordinate(self, relative_coordinate: List[float]) -> List[float]:
        """
        将LLM返回的相对坐标(基于1000x1000)转换为实际屏幕坐标
        
        Args:
            relative_coordinate: LLM返回的相对坐标 [x, y]，范围 [0, 1000]
        
        Returns:
            绝对坐标 [x, y]，基于实际截图尺寸
        """
        if not self.original_width or not self.original_height:
            return relative_coordinate
        
        # 从 1000x1000 转换到实际屏幕坐标
        absolute_x = relative_coordinate[0] / 1000.0 * self.original_width
        absolute_y = relative_coordinate[1] / 1000.0 * self.original_height
        
        return [absolute_x, absolute_y]

    def __call__(
        self,
        base64_screenshot: str,
        action: str,
        min_pixels: int = 3136,
        max_pixels: int = 12845056,
    ):
        """
        Perform GUI grounding using Qwen model to interpret user query on a screenshot.

        Args:
            base64_screenshot (str): Base64-encoded screenshot image
            action (str): User's query/instruction
            min_pixels: Minimum pixels for the image
            max_pixels: Maximum pixels for the image

        Returns:
            tuple: (completion, actions)
        """

        if base64_screenshot.startswith("data:"):
            base64_screenshot = base64_screenshot.split("base64,", 1)[-1]

        input_image = Image.open(io.BytesIO(base64.b64decode(base64_screenshot)))
        
        # 保存原始尺寸用于坐标转换
        self.original_width = input_image.width
        self.original_height = input_image.height

        resized_height, resized_width = smart_resize(
            input_image.height,
            input_image.width,
            factor=32,
            min_pixels=min_pixels,
            max_pixels=max_pixels,
        )

        # Initialize computer use function
        computer_use = ComputerUse(cfg={"display_width_px": 1000, "display_height_px": 1000})

        # Build messages
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

        completion = self.executor_client.chat.completions.create(
            model=self.executor_model,
            messages=messages,
        )

        output_text = completion.choices[0].message.content or ""

        action: Optional[Dict[str, Any]] = None
        if "<tool_call>" in output_text:
            tool_payload = output_text.split("<tool_call>\n", 1)[1].split("\n</tool_call>", 1)[
                0
            ]
            action = json.loads(tool_payload)
        else:
            try:
                action = json.loads(output_text)
            except json.JSONDecodeError:
                action = None

        actions: List[Dict[str, Any]] = []
        if action:
            actions.append(action)
            arguments = action.get("arguments", {})
            self._gui_action(arguments)

        return completion, actions
