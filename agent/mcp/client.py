"""
MCP 客户端包装器

基于官方 MCP Python SDK 的客户端实现
支持连接本地和远程 MCP 服务器
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import CallToolResult, TextContent


@dataclass
class MCPToolCall:
    """MCP工具调用"""
    server_name: str
    tool_name: str
    arguments: Dict[str, Any]


@dataclass
class MCPToolResult:
    """MCP工具调用结果"""
    success: bool
    server_name: str
    tool_name: str
    data: Any = None
    error_message: str = ""


class MCPClientManager:
    """
    MCP 客户端管理器
    
    管理多个 MCP 服务器的连接和工具调用
    """
    
    def __init__(self):
        self._logger = logging.getLogger(__name__)
        self._servers: Dict[str, Dict[str, Any]] = {}  # server_name -> {config, session, tools}
        self._initialized = False
        self._exit_stack = AsyncExitStack()
    
    async def add_server(self, name: str, config: Dict[str, Any]) -> bool:
        """
        添加并初始化一个 MCP 服务器
        
        Args:
            name: 服务器名称
            config: 服务器配置，例如:
                {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/home/user"],
                    "env": {"ENV_VAR": "value"}  # 可选
                }
        
        Returns:
            是否成功添加
        """
        try:
            # 创建服务器参数
            server_params = StdioServerParameters(
                command=config["command"],
                args=config.get("args", []),
                env=config.get("env")
            )
            
            # 建立连接 - 使用 AsyncExitStack 管理生命周期
            stdio_transport = await self._exit_stack.enter_async_context(stdio_client(server_params))
            read_stream, write_stream = stdio_transport
            
            # 创建会话
            session = await self._exit_stack.enter_async_context(ClientSession(read_stream, write_stream))
            await session.initialize()
            
            # 获取可用工具
            tools_response = await session.list_tools()
            tools = {tool.name: tool for tool in tools_response.tools}
            
            # 保存服务器信息
            self._servers[name] = {
                "config": config,
                "session": session,
                "tools": tools,
            }

            return True
            
        except Exception as e:
            self._logger.error(f"Failed to add MCP server '{name}': {e}", exc_info=True)
            return False
    
    async def remove_server(self, name: str):
        """
        移除 MCP 服务器
        
        Args:
            name: 服务器名称
        """
        if name not in self._servers:
            return
        
        try:
            del self._servers[name]
            self._logger.info(f"MCP server '{name}' removed from registry")
        except Exception as e:
            self._logger.error(f"Error removing MCP server '{name}': {e}")
    
    def list_servers(self) -> List[str]:
        """列出所有已连接的服务器"""
        return list(self._servers.keys())
    
    def list_tools(self, server_name: Optional[str] = None) -> Dict[str, List[str]]:
        """
        列出可用工具
        
        Args:
            server_name: 指定服务器名称，如果为None则返回所有服务器的工具
        
        Returns:
            {server_name: [tool_name, ...]}
        """
        if server_name:
            if server_name in self._servers:
                return {server_name: list(self._servers[server_name]["tools"].keys())}
            return {}
        
        return {
            name: list(info["tools"].keys())
            for name, info in self._servers.items()
        }
    
    def get_tool_info(self, server_name: str, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        获取工具信息
        
        Args:
            server_name: 服务器名称
            tool_name: 工具名称
        
        Returns:
            工具信息字典，包含 name, description, inputSchema
        """
        if server_name not in self._servers:
            return None
        
        tools = self._servers[server_name]["tools"]
        if tool_name not in tools:
            return None
        
        tool = tools[tool_name]
        return {
            "name": tool.name,
            "description": tool.description,
            "inputSchema": tool.inputSchema,
        }
    
    async def call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> MCPToolResult:
        """
        调用 MCP 工具
        
        Args:
            server_name: 服务器名称
            tool_name: 工具名称
            arguments: 工具参数
        
        Returns:
            MCPToolResult
        """
        if server_name not in self._servers:
            return MCPToolResult(
                success=False,
                server_name=server_name,
                tool_name=tool_name,
                error_message=f"Server '{server_name}' not found"
            )
        
        server_info = self._servers[server_name]
        session = server_info["session"]
        
        try:
            result: CallToolResult = await session.call_tool(tool_name, arguments)
            
            # 解析结果
            content_text = []
            for content in result.content:
                if isinstance(content, TextContent):
                    content_text.append(content.text)
            
            # 获取结构化数据（如果有）
            data = None
            if hasattr(result, 'structuredContent') and result.structuredContent:
                data = result.structuredContent
            elif content_text:
                data = "\n".join(content_text)
            
            return MCPToolResult(
                success=not result.isError,
                server_name=server_name,
                tool_name=tool_name,
                data=data,
                error_message="\n".join(content_text) if result.isError else ""
            )
            
        except Exception as e:
            self._logger.error(f"Error calling tool '{tool_name}' on server '{server_name}': {e}")
            return MCPToolResult(
                success=False,
                server_name=server_name,
                tool_name=tool_name,
                error_message=str(e)
            )
    
    async def close_all(self):
        """关闭所有服务器连接"""
        self._servers.clear()
        await self._exit_stack.aclose()
    
    def get_tools_for_prompt(self) -> str:
        """
        生成用于 LLM Prompt 的工具描述
        
        Returns:
            格式化的工具描述文本
        """
        if not self._servers:
            return "暂无可用的 MCP 工具"
        
        lines = ["### 可用的 MCP 工具"]
        
        for server_name, server_info in self._servers.items():
            lines.append(f"\n**{server_name}**:")
            for tool_name, tool in server_info["tools"].items():
                lines.append(f"  - {tool_name}: {tool.description}")
        
        return "\n".join(lines)


# 全局客户端管理器实例
_mcp_client_manager: Optional[MCPClientManager] = None


def get_mcp_client_manager() -> MCPClientManager:
    """
    获取全局 MCP 客户端管理器实例（单例模式）
    
    Returns:
        MCPClientManager 实例
    """
    global _mcp_client_manager
    if _mcp_client_manager is None:
        _mcp_client_manager = MCPClientManager()
    return _mcp_client_manager


def reset_mcp_client_manager():
    """重置全局 MCP 客户端管理器（主要用于测试）"""
    global _mcp_client_manager
    _mcp_client_manager = None
