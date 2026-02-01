# Telegram Bot 配置教程

本教程将指导你如何配置 Cappuccino 项目的 Telegram Bot，让你可以通过 Telegram 与 AI Agent 进行交互。

---

## 📋 准备工作

在开始之前，确保你已经：
- ✅ 安装了 Telegram 应用（手机或电脑版）
- ✅ 拥有一个 Telegram 账号

---

## 🤖 步骤 1：创建 Telegram Bot

### 1.1 找到 BotFather

1. 在 Telegram 中搜索 `@BotFather`（官方机器人管理工具）
2. 点击进入对话

### 1.2 创建新 Bot

1. 发送命令：`/newbot`
2. BotFather 会要求你给 Bot 起个名字，例如：`My Cappuccino Bot`
3. 然后要求你设置 Bot 的用户名（必须以 `bot` 结尾），例如：`mycappuccino_bot`
4. 创建成功后，BotFather 会给你一个 **Bot Token**，格式类似：
   ```
   123456789:ABCdefGHIjklMNOpqrsTUVwxyz1234567890
   ```
   ⚠️ **重要**：这个 Token 非常重要，请妥善保管，不要泄露！

### 1.3 其他可选设置

你可以继续向 BotFather 发送命令来配置 Bot：
- `/setdescription` - 设置 Bot 描述
- `/setabouttext` - 设置 Bot 关于信息
- `/setuserpic` - 设置 Bot 头像

---

## 🔑 步骤 2：获取你的 User ID（可选，用于权限控制）

如果你想限制只有特定用户可以使用 Bot，需要获取你的 Telegram User ID。

### 方法 1：使用 @userinfobot
1. 在 Telegram 中搜索 `@userinfobot`
2. 发送任意消息给它
3. 它会回复你的 User ID，例如：`123456789`

### 方法 2：使用 @getmyid_bot
1. 在 Telegram 中搜索 `@getmyid_bot`
2. 点击 Start
3. 它会回复你的 User ID

### 多用户配置
如果你想允许多个用户使用 Bot，可以分别获取他们的 User ID，稍后用逗号分隔配置。

---

## ⚙️ 步骤 3：配置项目

打开项目根目录下的 `.env` 文件，找到 Telegram 配置部分：

```bash
# ============================================
# 平台配置
# ============================================

# Telegram Bot 平台
TELEGRAM_ENABLED=false
TELEGRAM_BOT_TOKEN=
TELEGRAM_ALLOWED_USERS=
```

### 3.1 启用 Telegram Bot

将 `TELEGRAM_ENABLED` 改为 `true`：

```bash
TELEGRAM_ENABLED=true
```

### 3.2 填入 Bot Token

将步骤 1 中获得的 Token 填入 `TELEGRAM_BOT_TOKEN`：

```bash
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz1234567890
```

⚠️ 注意：不要加引号

### 3.3 配置授权用户（可选）

**情况 A：允许所有人使用（不推荐）**
```bash
TELEGRAM_ALLOWED_USERS=
```
留空即可，所有人都能使用你的 Bot。

**情况 B：只允许特定用户使用（推荐）**
```bash
TELEGRAM_ALLOWED_USERS=123456789
```

**情况 C：允许多个用户使用**
```bash
TELEGRAM_ALLOWED_USERS=123456789,987654321,555666777
```
用逗号分隔多个 User ID，中间不要有空格。

### 配置示例

完整的配置示例：

```bash
# Telegram Bot 平台
TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=6123456789:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw
TELEGRAM_ALLOWED_USERS=123456789,987654321
```

---

## 🚀 步骤 4：启动服务

保存 `.env` 文件后，启动服务器：

```bash
uv run python run_server.py
```

---

## 💬 步骤 5：开始使用

### 5.1 找到你的 Bot

在 Telegram 中搜索你在步骤 1.2 中设置的用户名（例如 `@mycappuccino_bot`）

### 5.2 启动对话

点击 `Start` 按钮或发送 `/start` 命令

### 5.3 可用命令

Bot 支持以下命令：

- `/start` - 开始使用，查看欢迎信息
- `/help` - 查看帮助信息和可用命令
- `/screenshot` - 获取当前屏幕截图
- `/run <任务描述>` - 执行任务，例如：
  ```
  /run 打开浏览器搜索Python教程
  ```

### 5.4 直接对话

你也可以直接发送消息（不带命令），Bot 会将其理解为 `/run` 命令：

```
打开记事本并输入Hello World
```

---

## 🔍 故障排查

### 问题 1：Bot 没有响应

**检查清单：**
- ✅ 确认服务器正在运行（`run_server.py` 没有报错）
- ✅ 确认 `TELEGRAM_ENABLED=true`
- ✅ 确认 Bot Token 正确（没有多余的空格或引号）
- ✅ 确认网络连接正常（Telegram API 需要科学上网）

**解决方法：**
1. 查看服务器日志，看是否有错误信息
2. 尝试重启服务器
3. 确认 Bot Token 是否有效（可以向 @BotFather 发送 `/mybots` 查看）

### 问题 2：Bot 回复"未授权"

**原因：**你的 User ID 不在允许列表中

**解决方法：**
1. 重新获取你的 User ID（参考步骤 2）
2. 将 User ID 添加到 `.env` 文件的 `TELEGRAM_ALLOWED_USERS` 中
3. 重启服务器

### 问题 3：Bot 响应很慢或超时

**可能原因：**
- 任务执行时间过长
- 网络延迟
- AI 模型响应慢

**解决方法：**
- 检查日志中的模型 API 调用情况
- 考虑使用更快的模型
- 检查网络连接质量

### 问题 4：Bot 报错"模型配置错误"

**解决方法：**
确保 `.env` 文件中的模型配置正确：
```bash
PLANNING_MODEL=gemini-3-flash-preview
PLANNING_API_KEY=sk-xxx...
PLANNING_BASE_URL=https://api5.xhub.chat/v1

GROUNDING_MODEL=qwen/qwen3-vl-8b-instruct
GROUNDING_API_KEY=sk-or-v1-xxx...
GROUNDING_BASE_URL=https://openrouter.ai/api/v1
```

---

## 🔐 安全建议

1. **保护 Bot Token**
   - 不要将 `.env` 文件提交到 Git（已添加到 `.gitignore`）
   - 不要在公开场合分享 Token
   - 如果 Token 泄露，立即通过 @BotFather 使用 `/revoke` 撤销并重新生成

2. **限制用户访问**
   - 强烈建议配置 `TELEGRAM_ALLOWED_USERS`
   - 只允许信任的用户使用 Bot
   - Bot 可以控制你的电脑，务必谨慎授权

3. **监控使用情况**
   - 定期检查日志文件（`logs/` 目录）
   - 注意异常的任务请求

---

## 📚 进阶配置

### 自定义 Bot 命令菜单

向 @BotFather 发送 `/setcommands`，然后选择你的 Bot，输入：

```
start - 开始使用
help - 查看帮助
screenshot - 获取屏幕截图
run - 执行任务
```

这样用户在输入 `/` 时会看到命令提示菜单。

### 设置 Bot 隐私模式

默认情况下，Bot 在群组中只能看到 @ 它的消息或以 `/` 开头的命令。

如果你想让 Bot 能看到群组中的所有消息：
1. 向 @BotFather 发送 `/setprivacy`
2. 选择你的 Bot
3. 选择 `Disable`

⚠️ 注意：当前版本不建议在群组中使用，因为 Bot 会控制你的电脑。

---

## ❓ 常见问题

**Q: 可以同时启用 URL API 和 Telegram Bot 吗？**  
A: 可以！两个平台可以同时运行，互不影响。

**Q: Bot 会记住之前的对话吗？**  
A: 会！每个用户都有独立的对话历史，存储在 SQLite 数据库中。

**Q: 如何停止 Bot？**  
A: 直接停止服务器（Ctrl+C）即可，或者将 `TELEGRAM_ENABLED` 改为 `false` 后重启。

**Q: 多个人可以同时使用同一个 Bot 吗？**  
A: 可以，但请确保理解风险：Bot 会在你的电脑上执行操作，多用户同时操作可能导致冲突。

**Q: 如何更换 Bot Token？**  
A: 向 @BotFather 发送 `/revoke` 撤销旧 Token，然后用 `/newbot` 创建新 Bot，或用 `/mybots` 选择现有 Bot 后用 `/token` 重新生成。

---

## 🎉 完成！

现在你可以通过 Telegram 随时随地控制你的 AI Agent 了！

如果遇到问题，请查看：
- 项目日志：`logs/` 目录
- 项目文档：`README.md`
- 架构说明：`ARCHITECTURE.md`

祝使用愉快！🚀
