<div align="center">
<h1><span style="font-size: 60px;">☕️</span> 卡布奇诺</h1>
<p>一个解放你双手的本地自动化智能体 🤖</p>
<p>放心将任务交予我，去静享一杯醇香的卡布奇诺 ☕️</p>
<p>待你悠然归来，任务早已悄然完成 🍃</p>
</div>

## 💡 概述

**卡布奇诺**是一个能操控电脑帮你解决繁琐任务的 GUI Agent，只需一条简单的指令，AI 就能生成详细的任务规划并执行。与解析图片元素或使用浏览器接口的其他现有方案不同，**卡布奇诺**是基于桌面屏幕的纯视觉方案。

你可以直接使用 API 调用模型快速上手，也可以接入 Telegram 使用手机操控。

## ✨ 特点

- **本地部署：** 本项目完全开源，可自行部署到自己的服务器并设置安全措施，保护您的隐私。
- **可拓展性：** 当前架构支持自定义添加更多的执行器以拓展 Agent 的能力。
- **软件适配：** 开发者可根据自身所需软件微调模型，让 Agent 获得更好的软件操控能力。

## 📰 更新

- **[2026/02/01]** 🏆 更新了系统架构、server，提供 Telegram 接入方式，暂不兼容客户端使用方式。
- **[2025/03/26]** ⌨️ 添加了代码执行器，能更好的生成文件。
- **[2025/02/27]** 🏆 现在你可以使用 qwen 和 gpt-4o 体验 cappuccino。

> 你的 star🌟 是我们更新的最大动力！

## 🎥 演示

https://github.com/user-attachments/assets/c3f7d0cc-a3c2-4ea3-956e-738bb1edda10

## 👨‍💻 快速开始

### 0. 硬件准备

目前该项目支持部署在 Windows 和 Mac，由于系统的快捷键和操作方式等差异，不同系统的体验可能会有区别，我们后续还会进行更多的系统适配。

### 1. 模型部署

本项目支持使用供应商的 API 或本地部署 LLM。若您需要本地部署，请使用 OpenAI 兼容的 API 服务，我们推荐使用 vLLM 进行部署，具体可以参考 [官网教程](https://qwen.readthedocs.io/zh-cn/latest/deployment/vllm.html#openai-compatible-api-service) 。

### 2. 服务端配置与启动

以下操作在需要被控制的计算机上执行。

#### 2.1 克隆仓库

```bash
git clone https://github.com/GML-FMGroup/cappuccino.git
cd cappuccino
```

#### 2.2 安装依赖

首先安装 uv（如果已安装可跳过）：

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# 或使用 pip
pip install uv
```

然后安装项目依赖：

```bash
uv sync
```

#### 2.3 启动服务

对于 Telegram 设置，请参考 TELEGRAM_SETUP.md 文档说明

```bash
uv run python run_server.py
```

### 3. 发送指令

在另一台设备上运行以发起网络请求。当然，你也可以在被控制的终端上运行，但我们建议使用另一台设备发送指令，以避免影响计算机的操作执行。

#### 方法 1：Python 脚本

1. 修改 `request_demo.py` 中的 Url 和 Access Token。例如，IP 为 192.168.0.100。
2. 填写 LLM 配置信息，如 API Key、供应商等。
3. 运行 Python 文件。
```bash
uv run python request_demo.py
```

#### 方法 2：Telegram

详情请参考 TELEGRAM_SETUP.md 文档说明

### ⚠️ 注意事项

- 选择模型时，请确保名称正确且供应商支持该模型。
- 我们当前的接口基于 openai 库实现。请确保供应商或本地部署支持提供的模型。
- 由于模型输出带有不稳定性，若运行失败，可尝试再次运行或修改问题。


