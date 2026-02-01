"""
URL/HTTP Bot Service - REST API Interface
Provides HTTP/REST endpoints for task execution and control.
Follows the same unified architecture as Telegram Bot:
  HTTP Request → URLBotService → Commands → Handlers → Agent
"""

from dataclasses import dataclass
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, Response
import logging

from ..messages import MSG_UNAUTHORIZED
from ..commands import parse_command, handle_start, handle_help, handle_screenshot, handle_run
from ..utils import encode_sse


logger = logging.getLogger(__name__)


@dataclass
class URLBotConfig:
    """URL API Bot configuration"""
    host: str = "0.0.0.0"
    port: int = 8000
    enabled: bool = True


class URLBotService:
    """
    HTTP REST API service for remote execution.
    
    Architecture:
    - Receives HTTP requests
    - Validates Bearer token authentication
    - Delegates to commands layer (same as Telegram bot)
    - Commands routes to appropriate handlers
    - Returns SSE-streamed responses
    
    Endpoints:
    - POST /chat: Execute task with streaming response
    - POST /screenshot: Get single screenshot JPEG
    - POST /screenshot/stream: Stream screenshots via SSE
    """
    
    def __init__(self, config: URLBotConfig, access_token: str):
        """
        Initialize URL Bot Service.
        
        Args:
            config: URLBotConfig with host, port, enabled
            access_token: Cryptographic token for authentication
        """
        self.config = config
        self.access_token = access_token
        self.app = FastAPI(title="URL Bot Service")
        self._setup_routes()
    
    def _setup_routes(self):
        """Register all HTTP endpoints"""
        self.app.post("/chat")(self._handle_chat)
        self.app.post("/screenshot")(self._handle_screenshot)
        self.app.post("/screenshot/stream")(self._handle_screenshot_stream)
    
    def _verify_token(self, request: Request) -> bool:
        """
        Verify Bearer token in Authorization header.
        
        Args:
            request: FastAPI request object
            
        Returns:
            True if token is valid, False otherwise
        """
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return False
        
        token = auth_header[7:]  # Remove "Bearer " prefix
        return token == self.access_token
    
    async def _handle_chat(self, request: Request):
        """
        Handle /chat endpoint - Execute task via unified command pipeline.
        
        Request body:
        {
            "user_query": "take a screenshot",
            "user_id": "123456",
            "enable_memory": true,
            "planner_model": "deepseek-v3",        # optional override
            "planner_api_key": "sk-xxx",            # optional override
            "planner_base_url": "https://...",      # optional override
            "dispatcher_model": "...",              # optional override
            "dispatcher_api_key": "sk-xxx",         # optional override
            "dispatcher_base_url": "https://...",   # optional override
            "executor_model": "...",                # optional override
            "executor_api_key": "sk-xxx",           # optional override
            "executor_base_url": "https://..."      # optional override
        }
        
        Processing:
        1. Verify Bearer token
        2. Parse request
        3. Route through commands layer (same as Telegram bot)
        4. Commands delegates to handlers for execution
        
        Returns:
            StreamingResponse with SSE-formatted messages
        """
        # Verify authentication
        if not self._verify_token(request):
            logger.warning(f"❌ POST /chat - 认证失败 - 无效的 Bearer token")
            return Response(
                content=MSG_UNAUTHORIZED,
                status_code=401,
                media_type="text/plain"
            )
        
        logger.debug(f"✅ POST /chat - Bearer token 验证通过")
        
        # Parse request
        try:
            data = await request.json()
            user_query = data.get("user_query", "").strip()
            user_id = str(data.get("user_id", "default"))
            enable_memory = data.get("enable_memory", False)
            
            logger.info(f"📨 POST /chat - 收到请求: user_id={user_id}, enable_memory={enable_memory}")
            logger.debug(f"   查询: {user_query[:80]}...")
            
            # Build request config for model overrides
            request_config = {
                "planner": {},
                "dispatcher": {},
                "executor": {}
            }

            if "planner_model" in data:
                request_config["planner"]["model"] = data["planner_model"]
                logger.debug(f"   planner 模型覆盖: {data['planner_model']}")
            if "planner_api_key" in data:
                request_config["planner"]["api_key"] = data["planner_api_key"]
                logger.debug("   planner API key 覆盖")
            if "planner_base_url" in data:
                request_config["planner"]["base_url"] = data["planner_base_url"]
                logger.debug(f"   planner base_url 覆盖: {data['planner_base_url']}")

            if "dispatcher_model" in data:
                request_config["dispatcher"]["model"] = data["dispatcher_model"]
                logger.debug(f"   dispatcher 模型覆盖: {data['dispatcher_model']}")
            if "dispatcher_api_key" in data:
                request_config["dispatcher"]["api_key"] = data["dispatcher_api_key"]
                logger.debug("   dispatcher API key 覆盖")
            if "dispatcher_base_url" in data:
                request_config["dispatcher"]["base_url"] = data["dispatcher_base_url"]
                logger.debug(f"   dispatcher base_url 覆盖: {data['dispatcher_base_url']}")

            if "executor_model" in data:
                request_config["executor"]["model"] = data["executor_model"]
                logger.debug(f"   executor 模型覆盖: {data['executor_model']}")
            if "executor_api_key" in data:
                request_config["executor"]["api_key"] = data["executor_api_key"]
                logger.debug("   executor API key 覆盖")
            if "executor_base_url" in data:
                request_config["executor"]["base_url"] = data["executor_base_url"]
                logger.debug(f"   executor base_url 覆盖: {data['executor_base_url']}")

            if not request_config["planner"]:
                request_config.pop("planner")
            if not request_config["dispatcher"]:
                request_config.pop("dispatcher")
            if not request_config["executor"]:
                request_config.pop("executor")
            
            if not user_query:
                logger.warning(f"❌ POST /chat - user_query 为空")
                return Response(
                    content=encode_sse({"type": "error", "message": "user_query is required"}),
                    status_code=400,
                    media_type="text/event-stream"
                )
        
        except Exception as e:
            logger.error(f"❌ POST /chat - 请求解析失败: {e}", exc_info=True)
            return Response(
                content=encode_sse({"type": "error", "message": f"Invalid request: {str(e)}"}),
                status_code=400,
                media_type="text/event-stream"
            )
        
        # Execute through command pipeline
        try:
            logger.info(f"🔄 POST /chat - 开始执行命令：{user_query}")
            
            async def stream_response():
                """
                Generator for SSE streaming response.
                
                Flow:
                1. Parse command (same as Telegram bot)
                2. Route through handle_* functions
                3. handle_run delegates to handlers.execute_task()
                """
                # Parse command using unified parser (same as telegram bot)
                cmd_type, cmd_arg = parse_command(user_query)
                logger.debug(f"   命令类型: {cmd_type.name}")
                
                # Route to command handlers
                if cmd_type.name == "START":
                    logger.info(f"   → 执行 START 命令")
                    result = handle_start()
                    yield encode_sse({
                        "type": "message",
                        "role": "assistant",
                        "content": result.message
                    })
                
                elif cmd_type.name == "HELP":
                    logger.info(f"   → 执行 HELP 命令")
                    result = handle_help()
                    yield encode_sse({
                        "type": "message",
                        "role": "assistant",
                        "content": result.message
                    })
                
                elif cmd_type.name == "SCREENSHOT":
                    result = handle_screenshot()
                    if result.success:
                        yield encode_sse({
                            "type": "screenshot",
                            "data": result.data.get("base64", "")
                        })
                    else:
                        yield encode_sse({
                            "type": "error",
                            "message": result.message
                        })
                
                else:  # RUN or TEXT - execute task via handlers
                    # Use cmd_arg if available (from /run prefix), otherwise use full query
                    query = cmd_arg if cmd_arg else user_query
                    
                    # Delegate to handlers layer (streaming execution)
                    async for stream_msg in handle_run(
                        query=query,
                        user_id=user_id,
                        request_config=request_config,
                        enable_memory=enable_memory
                    ):
                        yield encode_sse({
                            "type": "message",
                            "role": stream_msg.role,
                            "output": stream_msg.output,
                            "is_complete": stream_msg.is_complete,
                            "is_error": stream_msg.is_error
                        })
            
            return StreamingResponse(
                stream_response(),
                media_type="text/event-stream"
            )
        
        except Exception as e:
            logger.error(f"❌ POST /chat - 命令执行失败: {e}", exc_info=True)
            return Response(
                content=encode_sse({
                    "type": "error",
                    "message": f"Task execution failed: {str(e)}"
                }),
                status_code=500,
                media_type="text/event-stream"
            )
    
    async def _handle_screenshot(self, request: Request):
        """
        Handle /screenshot endpoint - Get single screenshot.
        
        Returns:
            JPEG image data with Content-Type: image/jpeg
        """
        # Verify authentication
        if not self._verify_token(request):
            return Response(
                content=MSG_UNAUTHORIZED,
                status_code=401,
                media_type="text/plain"
            )
        
        try:
            # Use unified command handler (same as HTTP)
            result = handle_screenshot()
            if result.success:
                image_data = result.data.get("image_bytes", b"")
                return Response(
                    content=image_data,
                    media_type="image/jpeg"
                )
            else:
                return Response(
                    content=result.message,
                    status_code=500,
                    media_type="text/plain"
                )
        except Exception as e:
            logger.error(f"Screenshot error: {e}", exc_info=True)
            return Response(
                content=f"Screenshot failed: {str(e)}",
                status_code=500,
                media_type="text/plain"
            )
    
    async def _handle_screenshot_stream(self, request: Request):
        """
        Handle /screenshot/stream endpoint - Stream screenshots via SSE.
        
        Returns:
            SSE stream of JPEG screenshots in base64
        """
        # Verify authentication
        if not self._verify_token(request):
            return Response(
                content=MSG_UNAUTHORIZED,
                status_code=401,
                media_type="text/plain"
            )
        
        try:
            async def stream_screenshots():
                """Generator for continuous screenshot streaming"""
                # Currently just return one screenshot
                # TODO: Implement continuous streaming with configurable interval
                result = handle_screenshot()
                if result.success:
                    yield encode_sse({
                        "type": "screenshot",
                        "data": result.data.get("base64", "")
                    })
                else:
                    yield encode_sse({
                        "type": "error",
                        "message": result.message
                    })
            
            return StreamingResponse(
                stream_screenshots(),
                media_type="text/event-stream"
            )
        
        except Exception as e:
            logger.error(f"Screenshot streaming error: {e}", exc_info=True)
            return Response(
                content=encode_sse({
                    "type": "error",
                    "message": f"Screenshot streaming failed: {str(e)}"
                }),
                status_code=500,
                media_type="text/event-stream"
            )
    
    def get_app(self) -> FastAPI:
        """Get FastAPI application instance for mounting"""
        return self.app
