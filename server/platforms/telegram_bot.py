"""
Telegram Bot 适配层
只负责 Telegram API 对接，业务逻辑委托给 commands 模块
"""

import io
import asyncio
from typing import Optional

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram.request import HTTPXRequest

from config import config
from server import messages
from server.commands import (
    handle_start,
    handle_help,
    handle_screenshot,
    handle_run,
)


class TelegramBotService:
    """Telegram Bot 适配层"""
    
    def __init__(self):
        self.app: Optional[Application] = None
        self.running_tasks = {}  # {user_id: task}
    
    def _is_authorized(self, user_id: int) -> bool:
        """检查用户是否授权"""
        if not config.telegram.allowed_users:
            return True
        return user_id in config.telegram.allowed_users
    
    async def _check_auth(self, update: Update) -> bool:
        """检查授权，未授权则回复"""
        if not self._is_authorized(update.effective_user.id):
            await update.message.reply_text(messages.MSG_UNAUTHORIZED)
            return False
        return True
    
    # ==================== 命令处理器 ====================
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /start 命令"""
        if not await self._check_auth(update):
            return
        result = handle_start()
        await update.message.reply_text(result.message)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /help 命令"""
        if not await self._check_auth(update):
            return
        result = handle_help()
        await update.message.reply_text(result.message)
    
    async def screenshot_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /screenshot 命令"""
        if not await self._check_auth(update):
            return
        
        await update.message.reply_text(messages.MSG_GETTING_SCREENSHOT)
        result = handle_screenshot()
        
        if result.success:
            image_bytes = result.data["image_bytes"]
            photo_buffer = io.BytesIO(image_bytes)
            photo_buffer.seek(0)
            await update.message.reply_photo(photo_buffer)
        else:
            await update.message.reply_text(result.message)
    
    async def run_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /run 命令"""
        if not await self._check_auth(update):
            return
        
        if not context.args:
            await update.message.reply_text(messages.MSG_NEED_QUERY)
            return
        
        query = " ".join(context.args)
        await self._execute_task(update, query)
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理普通文本消息（当作指令执行）"""
        if not await self._check_auth(update):
            return
        await self._execute_task(update, update.message.text)
    
    # ==================== 任务执行 ====================
    
    async def _execute_task(self, update: Update, query: str):
        """执行任务"""
        user_id = update.effective_user.id
        
        if user_id in self.running_tasks:
            await update.message.reply_text(messages.MSG_TASK_RUNNING)
            return
        
        # 发送开始消息
        await update.message.reply_text(messages.format_task_start(query))
        
        task = asyncio.create_task(
            self._stream_results(update, query, user_id)
        )
        self.running_tasks[user_id] = task
        
        try:
            await task
        finally:
            self.running_tasks.pop(user_id, None)
    
    async def _stream_results(self, update: Update, query: str, user_id: int):
        """流式接收并推送结果到 Telegram（每条消息独立发送）"""
        try:
            # 传递 user_id 给 handle_run，用于记忆管理
            async for stream_msg in handle_run(query, user_id=str(user_id)):
                if stream_msg.is_error:
                    await update.message.reply_text(
                        messages.format_task_error(stream_msg.error_message)
                    )
                    return
                
                # 格式化输出，每条都发送新消息
                text = messages.format_role_output(stream_msg.role, stream_msg.output)
                await update.message.reply_text(text)
                
                # 如果是完成消息（通常是reply），发送后就结束
                if stream_msg.is_complete:
                    return
        
        except asyncio.CancelledError:
            await update.message.reply_text(messages.MSG_TASK_CANCELLED)
        except Exception as e:
            await update.message.reply_text(messages.format_exec_error(str(e)))
    
    # ==================== 生命周期 ====================
    
    async def start(self):
        """启动 Telegram Bot"""
        if not config.telegram.bot_token:
            print("❌ Telegram Bot Token 未配置")
            return
        
        # 配置更长的超时时间，避免长时间运行的任务被中断
        # read_timeout: 等待服务器响应的超时时间（秒）
        # write_timeout: 发送请求的超时时间（秒）
        # connect_timeout: 建立连接的超时时间（秒）
        # pool_timeout: 从连接池获取连接的超时时间（秒）
        timeout = float(config.telegram.request_timeout)
        request = HTTPXRequest(
            connection_pool_size=8,
            read_timeout=timeout,       # 可配置的读取超时
            write_timeout=timeout,      # 可配置的写入超时
            connect_timeout=10.0,       # 10秒连接超时
            pool_timeout=10.0           # 10秒连接池超时
        )
        
        self.app = Application.builder().token(config.telegram.bot_token).request(request).build()
        
        # 注册命令处理器
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("run", self.run_command))
        self.app.add_handler(CommandHandler("screenshot", self.screenshot_command))
        
        # 处理普通消息
        self.app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )
        
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling(drop_pending_updates=True)
        
    async def stop(self):
        """停止 Telegram Bot"""
        if self.app:
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()
