import json
import os

class ocr_executor():
    """
    Parameters:
    - executor_client
    - executor_model (str): Model to be used by the executor client
    - controlledOS (str): The operating system being controlled
    - base64_screenshot (str): The base64 encoded screenshot
    - subtask (str): The subtask to be executed

    Returns:
    - completion (str): The full output of LLM
    - actions (arr): The action of the executed subtask
        - actions[0] (str): "ocr"
        - actions[1] (arr): The names of the extracted information
        - actions[2] (dict): The extracted
    """
    def __init__(self, executor_client, executor_model):
        self.executor_client = executor_client
        self.executor_model = executor_model
        self.controlledOS = os.environ["CONTROLLED_OS"]

    def _get_system_prompt(self):
        return f"""
You are a helpful assistant.
Please extract the text according to my needs and output according to json format.

## Output format:
```json
{{
    "Information name": "Extracted information content.",
}}
```
## Output example:
```json
{{
    "Bill Gates quote": "["Patience is a key element of success.","Don’t compare yourself with anyone in this world. If you do so, you are insulting yourself."]"
}}
```
"""
    
    def _parse_json(self, content):
        json_str = content.replace("```json","").replace("```","").strip()
        json_dict = json.loads(json_str)
        dict_names = []
        for key in json_dict:
            dict_names.append(key)
        return ["ocr", dict_names, json_dict]

    def __call__(self, base64_screenshot, subtask, min_pixels=3136, max_pixels=12845056):

        messages=[
            {
                "role": "system",
                "content": [{"type":"text","text": self._get_system_prompt()}],},
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
        content = completion.choices[0].message.content
        actions = self._parse_json(content)
        return completion, actions

