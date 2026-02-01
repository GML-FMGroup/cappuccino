"""
统一消息文本定义
所有 Bot 平台共用的文本内容
"""

# 欢迎语
WELCOME_MESSAGE = """🤖 Cappuccino Agent Bot

📝 使用方法：
/help - 查看帮助
/run <指令> - 执行任务
/screenshot - 获取截图

或直接发送文本指令"""

# 帮助文本
HELP_MESSAGE = """📖 命令说明：

🚀 /run <指令>
   执行 Agent 任务
   示例：/run 打开浏览器搜索 Python 教程

📸 /screenshot
   获取当前桌面截图

💡 提示：也可以直接发送文本指令，Bot 会自动执行"""

# 状态消息
MSG_UNAUTHORIZED = "❌ 未授权"
MSG_TASK_RUNNING = "⚠️ 已有任务运行中，请等待完成"
MSG_NEED_QUERY = "⚠️ 请提供指令，例如：/run 打开浏览器"
MSG_GETTING_SCREENSHOT = "📸 正在获取截图..."
MSG_SCREENSHOT_FAILED = "❌ 获取截图失败"
MSG_TASK_COMPLETE = "✅ 任务完成"
MSG_TASK_CANCELLED = "❌ 任务已取消"

# 格式化模板
def format_task_start(query: str) -> str:
    return f"🚀 执行：{query}"

def format_task_error(error: str) -> str:
    return f"❌ {error}"

def format_task_interrupt(error: str) -> str:
    return f"❌ 任务中断：{error}"

def format_exec_error(error: str) -> str:
    return f"❌ 执行错误：{error}"

# 角色图标
ROLE_ICONS = {
    "planner": "🧠",
    "dispatcher": "🤖",
    "executor": "✍️",
    "verifier": "🔍"
}

def format_role_output(role: str, output: dict) -> str:
    """格式化角色输出"""
    icon = ROLE_ICONS.get(role, "📌")
    
    if role == "planner":
        tasks = output.get("tasks", [])
        if tasks:
            return f"{icon} 规划器：找到 {len(tasks)} 个任务"
        return f"{icon} 规划器"
    
    elif role == "dispatcher":
        subtasks = output.get("subtasks", [])
        if subtasks:
            return f"{icon} 分发器：生成 {len(subtasks)} 个子任务"
        return f"{icon} 分发器"
    
    elif role == "executor":
        actions = output.get("actions", [])
        if actions:
            return f"{icon} 执行器：执行 {len(actions)} 个动作"
        return f"{icon} 执行器"
    
    elif role == "verifier":
        is_completed = output.get("is_completed", False)
        status = "✅ 已完成" if is_completed else "⏳ 未完成"
        return f"{icon} 校验器：{status}"
    
    return f"{icon} {role}"
