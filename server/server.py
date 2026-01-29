from pydantic import BaseModel, Field
from agent.agent import Agent
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
import io
import json
import random
import secrets
import socket
import asyncio
import pyautogui
import uvicorn

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


# 生成安全的 Access Token 用于所有接口认证
ACCESS_TOKEN = secrets.token_hex(32)  # 64字符的安全密钥
print(f"Generated Access Token: {ACCESS_TOKEN}")

app = FastAPI()

@app.post("/chat")
async def chat(request: Request):
    data = await request.json()
    # 验证 Access Token (可以从 header 或 body 中获取)
    access_token = request.headers.get("Authorization") or data.get("access_token")
    if access_token:
        # 支持 Bearer token 格式
        if access_token.startswith("Bearer "):
            access_token = access_token[7:]
    if access_token != ACCESS_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid access token")

    data = validate_and_update_data(data)
    print("The data has been received, and the agent execution starts")

    queue: asyncio.Queue = asyncio.Queue()

    async def send_callback(role, intermediate_output):
        intermediate_infor = {
            "message": "Process processing",
            "role": role,
            "intermediate_output": intermediate_output
        }
        await queue.put(intermediate_infor)

    async def run_agent():
        try:
            agent = Agent(send_callback, data)
            await agent.process()
            print("Process complete")
            await queue.put({"message": "Process complete"})
        except Exception as e:
            await queue.put({"message": "Process interruption", "error": f"{e}"})
        finally:
            await queue.put(None)

    asyncio.create_task(run_agent())

    async def event_generator():
        yield f"data: {json.dumps({'message': 'Access token verification passed'}, ensure_ascii=False)}\n\n"
        while True:
            item = await queue.get()
            if item is None:
                break
            yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )

@app.post("/screenshot")
async def screenshot(request: Request):
    """获取单张截图"""
    data = await request.json()
    # 验证 Access Token
    access_token = request.headers.get("Authorization") or data.get("access_token")
    if access_token and access_token.startswith("Bearer "):
        access_token = access_token[7:]
    if access_token != ACCESS_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid access token")

    screenshot = pyautogui.screenshot()
    screenshot = screenshot.resize((screenshot.width // 2, screenshot.height // 2))
    screenshot = screenshot.convert("RGB")
    screenshot_bytes = io.BytesIO()
    screenshot.save(screenshot_bytes, format="JPEG", quality=85)
    screenshot_bytes.seek(0)
    return Response(content=screenshot_bytes.read(), media_type="image/jpeg")

@app.post("/screenshot/stream")
async def screenshot_stream(request: Request):
    """SSE 流式推送截图，用于实时监控"""
    data = await request.json()
    # 验证 Access Token
    access_token = request.headers.get("Authorization") or data.get("access_token")
    if access_token and access_token.startswith("Bearer "):
        access_token = access_token[7:]
    if access_token != ACCESS_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid access token")

    async def screenshot_generator():
        yield f"data: {{\"message\": \"Screenshot stream started\"}}\n\n"
        try:
            while True:
                screenshot = pyautogui.screenshot()
                screenshot = screenshot.resize((screenshot.width // 2, screenshot.height // 2))
                screenshot = screenshot.convert("RGB")
                screenshot_bytes = io.BytesIO()
                screenshot.save(screenshot_bytes, format="JPEG", quality=85)
                screenshot_bytes.seek(0)
                
                # 将截图编码为 base64
                import base64
                screenshot_base64 = base64.b64encode(screenshot_bytes.read()).decode('utf-8')
                
                # 发送截图数据
                yield f"data: {{\"type\": \"screenshot\", \"data\": \"{screenshot_base64}\"}}\n\n"
                
                # 控制推送频率（每秒1帧）
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            yield f"data: {{\"message\": \"Screenshot stream stopped\"}}\n\n"

    return StreamingResponse(
        screenshot_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )

def main():
    """Run HTTP server with SSE for chat and HTTP polling for screenshots."""
    host = "0.0.0.0"
    port = 8000

    local_ip = get_local_ip()
    print("="*80)
    print(f"Chat SSE: POST http://{local_ip}:{port}/chat")
    print(f"Screenshot: POST http://{local_ip}:{port}/screenshot (单次获取)")
    print(f"Screenshot Stream: POST http://{local_ip}:{port}/screenshot/stream (实时监控)")
    print(f"")
    print(f"All endpoints require Access Token in Authorization header or 'access_token' field")
    print("="*80)

    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    main()
