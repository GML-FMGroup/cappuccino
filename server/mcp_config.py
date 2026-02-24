"""
MCP 服务器配置文件

在这里添加和配置 MCP (Model Context Protocol) 服务器
"""

# ============================================
# MCP 服务器配置
# ============================================
# 格式说明:
# "服务器名称": {
#     "command": "命令",
#     "args": ["参数1", "参数2", ...],
#     "env": {"环境变量": "值"}  # 可选
# }
# ============================================

MCP_SERVERS = {
    # 文件系统服务器 - 允许访问所有文件 (根目录)
    "filesystem": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/"]
    }

}


def get_mcp_servers():
    """
    获取 MCP 服务器配置
    
    Returns:
        dict: MCP 服务器配置字典
    """
    return MCP_SERVERS
