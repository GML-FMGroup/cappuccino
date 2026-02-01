"""
Unified Server - Multi-Platform Bot Orchestrator
Manages both Telegram and HTTP/URL API platforms through unified architecture.
All platforms share the same commands, handlers, and memory systems.
"""

import secrets
import socket
import asyncio
import threading
import uvicorn
import logging
from fastapi import FastAPI

from config import config
from .platforms.telegram_bot import TelegramBotService
from .platforms.url_bot import URLBotService, URLBotConfig
from .memory.manager import MemoryManager
from .logging_config import setup_logging

logger = logging.getLogger(__name__)


def get_local_ip():
    """Get the local machine's IP address"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception as e:
        return f"Error: {e}"


# Generate cryptographic Access Token for authentication
# ACCESS_TOKEN = secrets.token_hex(32)  # 64-character hex string
ACCESS_TOKEN = "1"  # 开发期间默认用 1 先


# Create main FastAPI app
app = FastAPI(title="Multi-Platform Bot Server")


def main():
    """
    Initialize and start multi-platform bot server.
    
    Features:
    - Setup enhanced logging system
    - Validates configuration
    - Initializes memory system
    - Starts enabled platforms (Telegram, URL API)
    - Manages platform lifecycle
    """
    
    # Initialize logging system (before any log output)
    setup_logging(log_level=config.server.log_level)
    
    logger.info("=" * 80)
    logger.info("🔧 初始化配置...")
    logger.info("=" * 80)
    
    print("=" * 80)
    print("🔧 初始化配置...")
    print("=" * 80)
    
    validation = config.validate()
    
    logger.info(f"配置验证结果: {validation}")
    
    print("=" * 80)
    
    # Model configuration must be complete
    if not (validation.get("planning") and validation.get("grounding")):
        print("❌ 模型配置不完整，无法启动服务")
        return
    
    # Initialize memory system
    MemoryManager.initialize(db_path="./data/memory.db")
    print("✅ 内存系统已初始化")
    
    # Get server configuration
    host = config.server.host
    port = config.server.port
    local_ip = get_local_ip()
    
    # Print startup information
    print("=" * 80)
    print("✨ 服务启动信息\n")
    print(f"Access Token: {ACCESS_TOKEN}")
    print("=" * 80)
    
    # Initialize URL API Bot (if enabled)
    if config.url_api.enabled:
        url_config = URLBotConfig(
            host=config.server.host,
            port=config.server.port,
            enabled=True
        )
        url_bot = URLBotService(config=url_config, access_token=ACCESS_TOKEN)
        url_app = url_bot.get_app()
        
        # Mount URL bot endpoints to main app
        app.mount("", url_app)
        
        print(f"✅ URL API 已启用")
        print(f"\n📡 访问地址:")
        print(f"   - 本地:     http://127.0.0.1:{port}")
        if local_ip and local_ip != "127.0.0.1":
            print(f"   - 局域网:   http://{local_ip}:{port}")
        print(f"\n📋 可用端点:")
        print(f"   - POST /chat")
        print(f"   - POST /screenshot")
        print(f"   - POST /screenshot/stream")
    else:
        print("⊘ URL API 未启用")
    
    print("=" * 80)
    
    # Initialize Telegram Bot (if enabled)
    if config.telegram.enabled:
        def run_telegram_bot():
            """Run Telegram bot in separate thread with its own event loop"""
            bot = TelegramBotService()
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                loop.run_until_complete(bot.start())
                loop.run_forever()
            except KeyboardInterrupt:
                loop.run_until_complete(bot.stop())
            finally:
                loop.close()
        
        bot_thread = threading.Thread(target=run_telegram_bot, daemon=True)
        bot_thread.start()
        print(f"✅ Telegram Bot 已启用 (后台运行)")
    else:
        print("⊘ Telegram Bot 未启用")
    
    print("=" * 80 + "\n")
    
    # Start HTTP server
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=config.server.log_level.lower()
    )
