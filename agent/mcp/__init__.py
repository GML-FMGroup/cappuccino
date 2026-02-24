"""
MCP (Model Context Protocol) 模块

基于官方 MCP Python SDK 的客户端实现
支持连接各种 MCP 服务器（文件系统、数据库、API 等）
"""

from .client import (
    MCPClientManager,
    MCPToolCall,
    MCPToolResult,
    get_mcp_client_manager,
    reset_mcp_client_manager,
)

__all__ = [
    "MCPClientManager",
    "MCPToolCall",
    "MCPToolResult",
    "get_mcp_client_manager",
    "reset_mcp_client_manager",
]
