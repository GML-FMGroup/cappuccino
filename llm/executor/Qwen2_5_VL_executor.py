import re
import json
import time
import base64
from openai import OpenAI
from computer.gui_action import GuiAction
from PIL import Image
from IPython.display import display
from transformers.models.qwen2_vl.image_processing_qwen2_vl_fast import smart_resize
from typing import Union, Tuple, List
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
* If you need to type a string of text, You should first left_click where you need to type and then type.
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
* `left_click_drag`: Click and drag the cursor to a specified (x, y) pixel coordinate on the screen.
* `right_click`: Click the right mouse button.
* `middle_click`: Click the middle mouse button.
* `double_click`: Double-click the left mouse button.
* `scroll`: Performs a scroll of the mouse scroll wheel.
* `wait`: Wait specified seconds for the change to happen.
* `terminate`: Terminate the current task and report its completion status.
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
                    "scroll",
                    "wait",
                    "terminate",
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
            "pixels": {
                "description": "The amount of scrolling to perform. Positive values scroll up, negative values scroll down. Required only by `action=scroll`.",
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
        self.controlledOS = cfg["controlledOS"]
        super().__init__(cfg)

    def call(self, params: Union[str, dict], **kwargs):
        params = self._verify_json_format_args(params)
        action = params["action"]
        if action in ["left_click", "right_click", "middle_click", "double_click"]:
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

    def _wait(self, time: int):
        raise NotImplementedError()

    def _terminate(self, status: str):
        raise NotImplementedError()


class Qwen2_5_VL_executor:
    def __init__(self, executor_api_key, executor_base_url, executor_model, controlledOS):
        self.executor_client = OpenAI(
            api_key=executor_api_key,
            base_url=executor_base_url,
        )
        self.executor_model = executor_model
        self.controlledOS = controlledOS

    def encode_image(self, image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    def _parse_tool_call(self, text):
        try:
            # 使用正则表达式提取所有 <tool_call> 和 </tool_call> 之间的内容
            matches = re.findall(r'<tool_call>\n(.*?)\n</tool_call>', text, re.DOTALL)
            # 将每个匹配的字符串解析为 JSON 对象
            actions = [json.loads(match) for match in matches]
        except:
            actions = []
        return actions

    def perform_executor(self, screenshot_path, task, min_pixels=3136, max_pixels=12845056):
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
        input_image = Image.open(screenshot_path)
        base64_image = self.encode_image(screenshot_path)

        resized_height, resized_width = smart_resize(
            input_image.height,
            input_image.width,
            min_pixels=min_pixels,
            max_pixels=max_pixels,
        )
        # Initialize computer use function
        computer_use = ComputerUse(
            cfg={"display_width_px": resized_width, "display_height_px": resized_height, "controlledOS": self.controlledOS}
        )
        gui_action = GuiAction(self.controlledOS)
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
                        # Pass in BASE64 image data. Note that the image format (i.e., image/{format}) must match the Content Type in the list of supported images. "f" is the method for string formatting.
                        # PNG image:  f"data:image/png;base64,{base64_image}"
                        # JPEG image: f"data:image/jpeg;base64,{base64_image}"
                        # WEBP image: f"data:image/webp;base64,{base64_image}"
                        "image_url": {"url": f"data:image/png;base64,{base64_image}"},
                    },
                    {"type": "text", "text": task},
                ],
            }
        ]

        completion = self.executor_client.chat.completions.create(
            model = self.executor_model,
            messages = messages,
            tool_choice = "required",   # qwen2.5-vl暂不支持此参数，不能稳定输出tool_call
            parallel_tool_calls = True
        )
        output_text = completion.choices[0].message.content
        # 解析模型输出
        actions = self._parse_tool_call(output_text)
        # 逐个执行动作
        for action in actions:
            gui_action.perform_action(action["arguments"])
            time.sleep(0.8)

        return output_text
