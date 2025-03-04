import base64
from openai import OpenAI
from .planner_utils import get_system_prompt, parse_tasks, encode_image

class general_planner:
    def __init__(self, planner_api_key, planner_base_url, planner_model, controlledOS):
        self.planner_client = OpenAI(
            api_key=planner_api_key,
            base_url=planner_base_url,
        )
        self.planner_model = planner_model
        self.controlledOS = controlledOS

    def __call__(self, screenshot_path, query, min_pixels=3136, max_pixels=12845056):
        base64_image = encode_image(screenshot_path)

        messages=[
            {
                "role": "system",
                "content": get_system_prompt(self.controlledOS),
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
        tasks = parse_tasks(output_text)
        return output_text, tasks