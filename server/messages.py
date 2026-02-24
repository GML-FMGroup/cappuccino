"""
统一消息文本定义
所有 Bot 平台共用的文本内容
"""

# Welcome Message
WELCOME_MESSAGE = """🤖 Cappuccino Agent Bot

📝 Usage:
/help - Show help
/run <command> - Execute task
/screenshot - Get screenshot

Or send text command directly"""

# Help Message
HELP_MESSAGE = """📖 Commands:

🚀 /run <command>
   Execute Agent task
   Example: /run open browser and search Python tutorial

📸 /screenshot
   Get current desktop screenshot

💡 Tip: You can also send text command directly"""

# Status Messages
MSG_UNAUTHORIZED = "❌ Unauthorized"
MSG_TASK_RUNNING = "⚠️ Task is already running, please wait"
MSG_NEED_QUERY = "⚠️ Please provide command, e.g.: /run open browser"
MSG_GETTING_SCREENSHOT = "📸 Getting screenshot..."
MSG_SCREENSHOT_FAILED = "❌ Failed to get screenshot"
MSG_TASK_COMPLETE = "✅ Task completed"
MSG_TASK_CANCELLED = "❌ Task cancelled"

# Format Templates
def format_task_start(query: str) -> str:
    return f"🚀 Executing: {query}"

def format_task_error(error: str) -> str:
    return f"❌ {error}"

def format_task_interrupt(error: str) -> str:
    return f"❌ Task interrupted: {error}"

def format_exec_error(error: str) -> str:
    return f"❌ Execution error: {error}"

# Role Icons
ROLE_ICONS = {
    "planner": "🧠",
    "executor": "🔧",
    "reply": "🤖"
}

def format_role_output(role: str, output: dict) -> str:
    """格式化角色输出"""
    icon = ROLE_ICONS.get(role, "📌")
    
    if role == "planner":
        # Display planning thinking and plan
        thinking = output.get("thinking", "")
        plan = output.get("plan", "")
        action = output.get("action", {})
        
        if action:
            # dispatcher mode
            action_type = action.get("type", "")
            if action_type == "execute":
                params = action.get("params", {})
                executor = params.get("executor", "")
                action_desc = params.get("action", "")
                return f"{icon} Planner\n💭 {thinking[:100]}...\n➡️ Next: {action_desc[:80]}..."
            elif action_type == "reply":
                return f"{icon} Planner\n💭 {thinking[:100]}...\n➡️ Replying to user"
            elif action_type == "save_info":
                params = action.get("params", {})
                key = params.get("key", "")
                return f"{icon} Planner\n💭 {thinking[:100]}...\n💾 Saving: {key}"
            elif action_type == "modify_plan":
                return f"{icon} Planner\n💭 {thinking[:100]}...\n🔄 Modifying plan"
        elif plan:
            # initial planning mode
            return f"{icon} Planner\n💭 {thinking[:100]}...\n📝 Plan: {plan[:100]}..."
        
        return f"{icon} Planner\n💭 {thinking[:150]}"
    
    elif role == "executor":
        actions = output.get("actions", [])
        executor_type = output.get("executor", "")
        action_desc = output.get("action", "")
        
        if actions and action_desc:
            # Display action summary
            action_summary = ", ".join([a.get("name", "") for a in actions[:3]])
            if len(actions) > 3:
                action_summary += f" +{len(actions)-3} more"
            return f"{icon} Executor\n🎯 Task: {action_desc[:80]}\n⌨️ Actions: {action_summary}"
        elif actions:
            return f"{icon} Executor: {len(actions)} action(s)"
        elif action_desc:
            return f"{icon} Executor\n🎯 {action_desc[:100]}"
        
        return f"{icon} Executor"
    
    elif role == "reply":
        message = output.get("message", "")
        if message:
            return f"{icon} {message}"
        return f"{icon} Reply"
    
    return f"{icon} {role}"
