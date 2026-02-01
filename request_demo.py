import asyncio
import json
import httpx

async def send_request():
    url = "http://127.0.0.1:8000/chat"  # HTTP SSE 服务地址
    
    # 将服务器生成的 Access Token 填入这里
    access_token = "1"  # 从服务器启动日志中复制
    
    # 简化请求：只传用户查询，模型配置从 .env 读取
    data = {
        "user_query": "打开代码随想录",
    }
    
    # 使用 Authorization header 传递 Access Token
    headers = {"Authorization": f"Bearer {access_token}"}

    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream("POST", url, json=data, headers=headers) as response:
            if response.status_code != 200:
                print("Request failed:", response.status_code, await response.aread())
                return

            async for line in response.aiter_lines():
                if not line or not line.startswith("data:"):
                    continue
                payload = line.replace("data:", "", 1).strip()
                try:
                    message = json.loads(payload)
                except json.JSONDecodeError:
                    print("Failed to decode JSON data")
                    continue

                print("Received JSON data:", message)
                if message.get("message") in {"Process complete", "Process interruption"}:
                    break


async def get_screenshot():
    """获取单张截图"""
    url = "http://127.0.0.1:8000/screenshot"
    access_token = "1"  # 与 chat 使用相同的 token
    
    headers = {"Authorization": f"Bearer {access_token}"}
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json={}, headers=headers)
        if response.status_code == 200:
            with open("screenshot.jpg", "wb") as f:
                f.write(response.content)
            print("Screenshot saved to screenshot.jpg")
        else:
            print("Failed to get screenshot:", response.status_code)


async def monitor_screenshots():
    """实时监控截图流（SSE 方式，更高效）"""
    url = "http://127.0.0.1:8000/screenshot/stream"
    access_token = "1"  # 与 chat 使用相同的 token
    
    headers = {"Authorization": f"Bearer {access_token}"}
    
    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream("POST", url, json={}, headers=headers) as response:
            if response.status_code != 200:
                print("Failed to start screenshot stream:", response.status_code)
                return
            
            print("Screenshot stream started, receiving frames...")
            frame_count = 0
            async for line in response.aiter_lines():
                if not line or not line.startswith("data:"):
                    continue
                payload = line.replace("data:", "", 1).strip()
                try:
                    message = json.loads(payload)
                    if message.get("type") == "screenshot":
                        frame_count += 1
                        # 解码 base64 并保存（这里只是示例，实际可以显示或处理）
                        import base64
                        screenshot_data = base64.b64decode(message["data"])
                        # 可选：每隔10帧保存一次
                        if frame_count % 10 == 0:
                            with open(f"monitor_frame_{frame_count}.jpg", "wb") as f:
                                f.write(screenshot_data)
                            print(f"Saved frame {frame_count}")
                    elif message.get("message"):
                        print("Server message:", message["message"])
                except json.JSONDecodeError:
                    continue
                except KeyboardInterrupt:
                    print("Stopping screenshot monitoring...")
                    break


# 运行聊天请求
asyncio.run(send_request())

# 如果需要获取单张截图，取消下面的注释
# asyncio.run(get_screenshot())

# 如果需要实时监控截图流，取消下面的注释
# asyncio.run(monitor_screenshots())


