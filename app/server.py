from pydantic import BaseModel, Field
from agent import Agent
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import io
import random
import socket
import asyncio
import pyautogui
import uvicorn
import threading
from uvicorn.config import Config
from uvicorn.server import Server

# message 状态说明
# Invalid token: token错误
# Token verification passed: token验证通过
# Process processing: 处理中
# Successfully obtained data: 成功获取数据（在处理中时，由客户端发送，用于保持连接）
# Process complete: 处理完成
# Process interruption: 处理中断

OPENAI_URL = "https://api.openai.com/v1"
DASHSCOPE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
SILICONFLOW_URL = "https://api.siliconflow.cn/v1"
MODELSCOPE_URL = "https://api-inference.modelscope.cn/v1/"

class RequestParams(BaseModel):
    planner_model: str = Field(None, description="Model used by the planner")
    planner_provider: str = Field(None, description="Provider for the planner: 'local', 'openai', 'dashscope', or 'siliconflow'")
    planner_api_key: str = Field(None, description="API key for the planner provider, required if the provider is not 'local'")
    planner_base_url: str = Field(None, description="Base URL for the planner provider, required if the provider is 'local'")
    dispatcher_model: str = Field(None, description="Model used by the dispatcher")
    dispatcher_provider: str = Field(None, description="Provider for the dispatcher: 'local', 'dashscope', or 'siliconflow'")
    dispatcher_api_key: str = Field(None, description="API key for the dispatcher provider, required if the provider is not 'local'")
    dispatcher_base_url: str = Field(None, description="Base URL for the dispatcher provider, required if the provider is 'local'")
    executor_model: str = Field(..., description="Model used by the executor")
    executor_provider: str = Field(..., description="Provider for the executor: 'local', 'dashscope', or 'siliconflow'")
    executor_api_key: str = Field(None, description="API key for the executor provider, required if the provider is not 'local'")
    executor_base_url: str = Field(None, description="Base URL for the executor provider, required if the provider is 'local'")
    user_query: str = Field(None, description="User's query, required if the agent type is 'planner'")

def predefined_url(data: dict) -> dict:
    provider_urls = {
        "openai": OPENAI_URL,
        "dashscope": DASHSCOPE_URL,
        "siliconflow": SILICONFLOW_URL,
        "modelscope": MODELSCOPE_URL,
    }
    if data["planner_provider"] in provider_urls:
        data["planner_base_url"] = provider_urls[data["planner_provider"]]
    if data["dispatcher_provider"] in provider_urls:
        data["dispatcher_base_url"] = provider_urls[data["dispatcher_provider"]]
    if data["executor_provider"] in provider_urls:
        data["executor_base_url"] = provider_urls[data["executor_provider"]]
    return data

def validate_and_update_data(data: dict) -> dict:
    for field in RequestParams.model_fields:  # Updated from __fields__ to model_fields
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


# 生成一个6位数的token
token = str(random.randint(100000, 999999))
print(f"Generated token: {token}")

# 创建两个单独的 FastAPI 实例，一个用于聊天，一个用于截图
chat_server = FastAPI()
screenshot_server = FastAPI()

@chat_server.websocket("/chat")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()

    try:
        # 验证token，避免异常接口调用
        received_token = await websocket.receive_json()
        if received_token.get("token") != token:
            await websocket.send_json({"message": "Invalid token"})
            await websocket.close()
            return
        else:
            await websocket.send_json({"message": "Token verification passed"})

        async def send_callback(role, intermediate_output):
            # 发送处理过程的信息
            intermediate_infor = {
                "message": "Process processing",
                "role": role,
                "intermediate_output": intermediate_output
            }
            await websocket.send_json(intermediate_infor)
            await websocket.receive_json()

        while True:
            # 接收数据并处理
            data = await websocket.receive_json()
            data = validate_and_update_data(data)
            print("The data has been received, and the agent execution starts")
            
            # 使用 create_task 来确保 agent.process() 不会阻塞事件循环
            agent = Agent(send_callback, data)
            await agent.process()
            
            # 返回处理结果
            print("Process complete")
            await websocket.send_json({"message": "Process complete"})

    except WebSocketDisconnect:
        pass

    except Exception as e:
        await websocket.send_json({"message": "Process interruption", "error": f"{e}"})

@screenshot_server.websocket("/screenshots")
async def websocket_screenshots(websocket: WebSocket):
    await websocket.accept()
    connection_active = True

    try:
        # 验证token
        received_token = await websocket.receive_json()
        if received_token.get("token") != token:
            await websocket.send_json({"message": "Invalid token"})
            await websocket.close()
            return
        else:
            await websocket.send_json({"message": "Token verification passed"})
        
        # 定期发送截图
        while connection_active:
            try:
                # Capture and send a screenshot with reduced resolution
                screenshot = pyautogui.screenshot()
                screenshot = screenshot.resize((screenshot.width // 2, screenshot.height // 2))
                screenshot = screenshot.convert("RGB")
                screenshot_bytes = io.BytesIO()
                screenshot.save(screenshot_bytes, format='JPEG')
                screenshot_bytes.seek(0)
                
                # 发送截图
                await websocket.send_bytes(screenshot_bytes.read())
                
                # 等待一秒后发送下一张截图
                await asyncio.sleep(0.2)
            except WebSocketDisconnect:
                connection_active = False
                break
            except Exception as inner_e:
                print(f"Error capturing/sending screenshot: {inner_e}")
                if "close message has been sent" in str(inner_e):
                    print("Connection closed, stopping screenshot sending")
                    connection_active = False
                    break
                await asyncio.sleep(0.2)  # 即使发生错误也等待，避免错误循环过快
                
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"Screenshot connection error: {e}")
    finally:
        # 确保在任何情况下都标记连接已关闭
        connection_active = False

def run_screenshot_server():
    """Run the screenshots WebSocket server in a separate process."""
    config = Config(app=screenshot_server, host="0.0.0.0", port=8001, log_level="info")
    server = Server(config=config)
    # Use a new event loop for the screenshots server
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(server.serve())

def main():
    """Run both the chat and screenshots WebSocket servers."""
    host = "0.0.0.0"
    chat_port = 8000
    screenshot_port = 8001
    
    local_ip = get_local_ip()
    print(f"Chat WebSocket: ws://{local_ip}:{chat_port}/chat")
    print(f"Screenshots WebSocket: ws://{local_ip}:{screenshot_port}/screenshots")
    
    # Start the screenshots server in a separate thread
    screenshot_thread = threading.Thread(target=run_screenshot_server, daemon=True)
    screenshot_thread.start()
    
    # Run the chat server in the main thread
    uvicorn.run(chat_server, host=host, port=chat_port)

if __name__ == "__main__":
    main()
