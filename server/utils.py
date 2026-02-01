"""
Server Utilities
Helper functions for SSE encoding, logging, and other utilities.
"""

import json
import logging

logger = logging.getLogger(__name__)


def encode_sse(data: dict) -> str:
    """
    Encode data as Server-Sent Event (SSE) format.
    
    Format: data: {json}\n\n
    
    Args:
        data: Dictionary to encode as JSON
        
    Returns:
        SSE-formatted string ready to send to client
    """
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def format_log(level: str, message: str, **kwargs) -> str:
    """
    Format log message with context.
    
    Args:
        level: Log level (INFO, ERROR, WARNING, DEBUG)
        message: Main message
        **kwargs: Additional context to include
        
    Returns:
        Formatted log message
    """
    if kwargs:
        context = " | ".join(f"{k}={v}" for k, v in kwargs.items())
        return f"[{level}] {message} | {context}"
    return f"[{level}] {message}"
