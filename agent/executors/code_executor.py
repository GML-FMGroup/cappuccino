import os
import builtins
import platform
import sys
import shutil  # Add this import for file operations

class code_executor():
    """
    Parameters:
    - executor_client
    - executor_model (str): Model to be used by the executor client
    - subtask (str): The subtask to be executed

    Returns:
    - completion (str): The full output of LLM
    - actions (arr): The action of the executed subtask
    """
    def __init__(self, executor_client, executor_model):
        self.executor_client = executor_client
        self.executor_model = executor_model
        self.controlledOS = platform.system()
        self.run_folder = os.environ["RUN_FOLDER"]

    def _get_system_prompt(self):
        return f"""
You are a helpful assistant.
The system you are currently operating is {self.controlledOS}.
Please generate executable code according to my task in the following format.
You can use code to generate word, excel, ppt, txt, pdf, markdown.
After saving the file, open the file by default.

## Output format:
```python
<executable code>
```

## Output example:
```python
import openpyxl
import os

# 创建一个新的 Excel 工作簿
wb = openpyxl.Workbook()
ws = wb.active
ws.title = "Sheet1"

# 添加一些示例数据
data = [
    ["姓名", "年龄", "成绩"],
    ["张三", 20, 85],
    ["李四", 22, 90],
    ["王五", 21, 88]
]

for row in data:
    ws.append(row)

# 保存 Excel 文件
filename = "sample.xlsx"
wb.save(filename)
```
"""
    
    def _parse_code(self, content):
        code = content.replace("```python","").replace("```","").strip()
        return [{"name": "code_generate", "arguments": code}]
    
    def _code_action(self, code):
        # Save current directory to return to it later
        original_dir = os.getcwd()
        target_dir = os.path.join(original_dir, self.run_folder)

        # Get list of files in the target directory before execution
        files_before = set(os.listdir(target_dir))
        
        try:
            # Change to the target directory before executing code
            os.chdir(target_dir)
            
            # Execute the code in the target directory
            exec(code)
            
            # Get list of files after execution to find new files
            files_after = set(os.listdir(target_dir))
            new_files = files_after - files_before
                
            if not new_files:
                print("No new files found in target directory")
                return
            
            for filename in new_files:
                file_path = os.path.join(target_dir, filename)
                
                # Auto open the file (it's already in the target directory)
                if self.controlledOS == "Windows":
                    os.startfile(file_path)  # For Windows
                elif self.controlledOS == "Darwin":
                    os.system(f'open "{file_path}"')  # For macOS
                elif self.controlledOS == "Linux":
                    os.system(f'xdg-open "{file_path}"')  # For Linux
                
        finally:
            # Return to original directory regardless of success or failure
            os.chdir(original_dir)


    def __call__(self, subtask, min_pixels=3136, max_pixels=12845056):
        messages=[
            {
                "role": "system",
                "content": [{"type":"text","text": self._get_system_prompt()}],
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": subtask},
                ],
            }
        ]
        completion = self.executor_client.chat.completions.create(
            model = self.executor_model,
            messages = messages,
        )
        content = completion.choices[0].message.content
        actions = self._parse_code(content)
        self._code_action(actions[0]["arguments"])
        return completion, actions

