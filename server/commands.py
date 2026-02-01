"""
统一命令处理器
负责命令解析和路由（轻量级）
复杂任务委托给 handlers 处理
"""

import io
import logging
from typing import AsyncGenerator, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

import pyautogui

from server import messages
from server.handlers import task_handler, StreamMessage

logger = logging.getLogger(__name__)


class CommandType(Enum):
    """命令类型"""
    START = "start"
    HELP = "help"
    RUN = "run"
    SCREENSHOT = "screenshot"
    TEXT = "text"  # 普通文本（当作 run 处理）


@dataclass
class CommandResult:
    """命令执行结果"""
    success: bool
    message: str = ""
    data: Any = None  # 可以是文本、图片 bytes 等


def parse_command(text: str) -> tuple[CommandType, str]:
    """
    解析命令
    
    Returns:
        (命令类型, 参数)
    """
    text = text.strip()
    logger.debug(f"解析命令: '{text}'")
    
    if text.startswith("/start"):
        logger.info("📍 命令类型: START")
        return CommandType.START, ""
    elif text.startswith("/help"):
        logger.info("📍 命令类型: HELP")
        return CommandType.HELP, ""
    elif text.startswith("/screenshot"):
        logger.info("📍 命令类型: SCREENSHOT")
        return CommandType.SCREENSHOT, ""
    elif text.startswith("/run"):
        # 提取 /run 后面的参数
        args = text[4:].strip()
        logger.info(f"📍 命令类型: RUN, 参数: '{args}'")
        return CommandType.RUN, args
    else:
        # 普通文本当作指令
        logger.debug(f"📍 命令类型: TEXT (当作 RUN 处理)")
        return CommandType.TEXT, text


def handle_start() -> CommandResult:
    """处理 /start 命令"""
    return CommandResult(success=True, message=messages.WELCOME_MESSAGE)


def handle_help() -> CommandResult:
    """处理 /help 命令"""
    return CommandResult(success=True, message=messages.HELP_MESSAGE)


def handle_screenshot() -> CommandResult:
    """
    处理 /screenshot 命令
    直接截图，返回 JPEG bytes 和 base64
    """
    try:
        import base64
        
        logger.debug("📸 开始截图...")
        screenshot = pyautogui.screenshot()
        screenshot = screenshot.resize((screenshot.width // 2, screenshot.height // 2))
        screenshot = screenshot.convert("RGB")
        screenshot_bytes = io.BytesIO()
        screenshot.save(screenshot_bytes, format="JPEG", quality=85)
        screenshot_bytes.seek(0)
        
        image_data = screenshot_bytes.read()
        base64_data = base64.b64encode(image_data).decode('utf-8')
        
        logger.info(f"✅ 截图成功: {len(image_data)} bytes")
        
        return CommandResult(
            success=True, 
            data={
                "image_bytes": image_data,
                "base64": base64_data
            }
        )
    except Exception as e:
        logger.error(f"❌ 截图失败: {e}", exc_info=True)
        return CommandResult(success=False, message=f"{messages.MSG_SCREENSHOT_FAILED}: {e}")


async def handle_run(
    query: str,
    user_id: str = "default",
    request_config: Optional[Dict] = None,
    enable_memory: bool = True
) -> AsyncGenerator[StreamMessage, None]:
    """
    处理 /run 命令，委托给 handlers 处理
    
    Args:
        query: 用户指令
        user_id: 用户 ID（用于记忆管理）
        request_config: 请求级别的配置覆盖
        enable_memory: 是否启用记忆
    
    Yields:
        StreamMessage: 流式消息
    """
    if not query:
        yield StreamMessage(
            role="error",
            output={},
            is_error=True,
            error_message=messages.MSG_NEED_QUERY
        )
        return
    
    # 委托给 TaskHandler 处理
    async for stream_msg in task_handler.execute_task(
        user_id=user_id,
        query=query,
        request_config=request_config,
        enable_memory=enable_memory
    ):
        yield stream_msg


# 便捷函数：执行命令
async def execute_command(
    command_type: CommandType,
    args: str = "",
    user_id: str = "default",
    request_config: Optional[Dict] = None
) -> CommandResult | AsyncGenerator[StreamMessage, None]:
    """
    执行命令的便捷入口
    
    对于 START, HELP, SCREENSHOT 返回 CommandResult
    对于 RUN, TEXT 返回 AsyncGenerator
    """
    if command_type == CommandType.START:
        return handle_start()
    elif command_type == CommandType.HELP:
        return handle_help()
    elif command_type == CommandType.SCREENSHOT:
        return handle_screenshot()
    elif command_type in (CommandType.RUN, CommandType.TEXT):
        return handle_run(args, user_id=user_id, request_config=request_config)
    else:
        return CommandResult(success=False, message="未知命令")
