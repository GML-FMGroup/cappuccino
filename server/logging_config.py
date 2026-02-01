"""
Logging Configuration - Enhanced Logging System
Provides detailed logging with file output and structured format.
"""

import logging
import logging.handlers
from pathlib import Path
from datetime import datetime


def setup_logging(log_level: str = "INFO", log_file: str = None):
    """
    Setup comprehensive logging system.
    
    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path for log output
                 If None, uses ./logs/server_{timestamp}.log
    """
    
    # Create logs directory if it doesn't exist
    log_dir = Path("./logs")
    log_dir.mkdir(exist_ok=True)
    
    # Generate log filename if not provided
    if log_file is None:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        log_file = log_dir / f"server_{timestamp}.log"
    else:
        log_file = log_dir / log_file
    
    # Convert string level to logging level
    log_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)  # 根据配置的日志级别设置
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Detailed format for files and console
    detailed_format = (
        "%(asctime)s | "
        "%(levelname)-8s | "
        "%(name)-30s | "
        "%(funcName)-20s | "
        "%(message)s"
    )
    
    simple_format = "%(levelname)-8s | %(name)-20s | %(message)s"
    
    # Console handler - 禁用（不输出到控制台）
    # console_handler = logging.StreamHandler()
    # console_handler.setLevel(log_level)
    # console_formatter = logging.Formatter(simple_format)
    # console_handler.setFormatter(console_formatter)
    # root_logger.addHandler(console_handler)
    
    # File handler (写入所有级别，但过滤由 root logger 的级别控制)
    try:
        file_handler = logging.FileHandler(
            log_file,
            encoding='utf-8'
        )
        file_handler.setLevel(log_level)  # 根据配置的日志级别设置
        file_formatter = logging.Formatter(detailed_format)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
        
        print(f"📝 日志文件: {log_file}")
    except Exception as e:
        print(f"⚠️  无法创建日志文件: {e}")
    
    # Suppress noisy loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    
    return root_logger
