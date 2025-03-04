from pydantic import BaseModel, Field
from agent import Agent
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import os
import io
import random
import socket

# message 状态说明
# Invalid token: token错误
# Token verification passed: token验证通过
# Process processing: 处理中
# Successfully obtained data: 成功获取数据（在处理中时，由客户端发送，用于保持连接）
# Processing complete: 处理完成
# Process interruption: 处理中断

OPENAI_URL = "https://api.openai.com/v1"
DASHSCOPE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
SILICONFLOW_URL = "https://api.siliconflow.cn/v1"

class RequestParams(BaseModel):
    agent_type: str = Field(..., description="planner or workflow")
    planner_model: str = Field(None, description="Model used by the planner")
    planner_provider: str = Field(None, description="Provider for the planner: 'local', 'openai', 'dashscope', or 'siliconflow'")
    planner_api_key: str = Field(None, description="API key for the planner provider, required if the provider is not 'local'")
    planner_base_url: str = Field(None, description="Base URL for the planner provider, required if the provider is 'local'")
    executor_model: str = Field(..., description="Model used by the executor")
    executor_provider: str = Field(..., description="Provider for the executor: 'local', 'dashscope', or 'siliconflow'")
    executor_api_key: str = Field(None, description="API key for the executor provider, required if the provider is not 'local'")
    executor_base_url: str = Field(None, description="Base URL for the executor provider, required if the provider is 'local'")
    user_query: str = Field(None, description="User's query, required if the agent type is 'planner'")
    user_tasks: list = Field(None, description="List containing multiple simple instructions, required if the agent type is 'workflow'")

def predefined_url(data: dict) -> dict:
    # 自动配置第三方供应商的base_url
    if data["agent_type"] == "planner":
        if data["planner_provider"] == "openai":
            data["planner_base_url"] = OPENAI_URL
        elif data["planner_provider"] == "dashscope":
            data["planner_base_url"] = DASHSCOPE_URL
        elif data["planner_provider"] == "siliconflow":
            data["planner_base_url"] = SILICONFLOW_URL

    if data["executor_provider"] == "openai":
        data["executor_base_url"] = OPENAI_URL
    elif data["executor_provider"] == "dashscope":
        data["executor_base_url"] = DASHSCOPE_URL
    elif data["executor_provider"] == "siliconflow":
        data["executor_base_url"] = SILICONFLOW_URL

    return data

def validate_and_update_data(data: dict) -> dict:
    for field in RequestParams.__fields__:
        if field not in data:
            data[field] = ""
    data = predefined_url(data)
    return data

def get_local_ip():
    try:
        # 创建一个 UDP socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # 连接到外部服务器（不会真正建立连接）
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception as e:
        return f"Error: {e}"

# 输出本机局域网 IP
print(f"Local IP Address: {get_local_ip()}")

# 生成一个6位数的token
token = str(random.randint(100000, 999999))
print(f"Generated token: {token}")

# 创建 FastAPI 实例
server = FastAPI()

@server.websocket("/chat")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()

    if not os.path.exists('temp'):
        os.makedirs('temp')

    try:
        # 验证token，避免异常接口调用
        received_token = await websocket.receive_json()
        if received_token.get("token") != token:
            await websocket.send_json({"message": "Invalid token"})
            await websocket.close()
            return
        else:
            await websocket.send_json({"message": "Token verification passed"})

        async def send_callback(intermediate_output, is_send_image=False):
            # 发送处理过程的信息
            intermediate_infor = {
                "message": "Process processing",
                "intermediate_output": intermediate_output
            }
            if is_send_image:
                # Capture and send a screenshot with reduced resolution
                import pyautogui
                screenshot = pyautogui.screenshot()
                screenshot = screenshot.resize((screenshot.width // 2, screenshot.height // 2))  # Reduce resolution by half
                screenshot = screenshot.convert("RGB")  # Convert to RGB mode
                screenshot_bytes = io.BytesIO()
                screenshot.save(screenshot_bytes, format='JPEG')
                screenshot_bytes.seek(0)
                await websocket.send_bytes(screenshot_bytes.read())
            await websocket.send_json(intermediate_infor)
            await websocket.receive_json()

        while True:
            # 接收数据并处理
            data = await websocket.receive_json()
            data = validate_and_update_data(data)

            # 调用agent处理数据
            agent = Agent(send_callback, data)
            await agent.process()

            # 返回处理结果
            await websocket.send_json({"message": "Processing complete"})


    except WebSocketDisconnect:
        print("Client disconnected")

    except Exception as e:
        await websocket.send_json({"message": "Process interruption", "error": f"{e}"})
