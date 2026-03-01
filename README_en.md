<div align="center">
<h1><span style="font-size: 60px;">☕️</span> Cappuccino</h1>
<p>A local automation agent that frees your hands 🤖</p>
<p>Trust your tasks to me, and enjoy a cup of aromatic cappuccino ☕️</p>
<p>When you return leisurely, the task has already been quietly completed 🍃</p>
<p align="center"><a href="README.md">中文文档</a></p>
</div>

## 💡 Overview

**Cappuccino** is a GUI Agent that can control your computer to solve tedious tasks. With just a simple instruction, AI can generate detailed task plans and execute them. Unlike other existing solutions that parse image elements or use browser interfaces, **Cappuccino** is a pure visual solution based on desktop screens.

You can quickly get started using API calls to the model, or connect to Telegram for mobile control.

## ✨ Features

- **Local Deployment:** This project is fully open source and can be self-deployed on your own servers with security measures to protect your privacy.
- **Extensibility:** The current architecture supports custom addition of more executors to expand Agent capabilities.
- **Software Adaptation:** Developers can fine-tune the model according to their required software to give the Agent better software control capabilities.

## 📰 Updates

- **[2026/02/24]** 🔧 Added MCP module, now supports connecting to MCP to enhance Agent capabilities.
- **[2026/02/01]** 🏆 Updated system architecture and server, provided Telegram integration method, temporarily incompatible with client usage.
- **[2025/03/26]** ⌨️ Added code executor for better file generation.
- **[2025/02/27]** 🏆 Now you can experience cappuccino using qwen and gpt-4o.

> Your star🌟 is our greatest motivation for updates!

## 🎥 Demo

https://github.com/user-attachments/assets/5949cd2f-92f1-4e2a-a1da-831cb7e08607

## 👨‍💻 Quick Start

### 0. Hardware Requirements

Currently, this project supports deployment on Windows and Mac. Due to differences in system shortcuts and operation methods, the experience may vary across different systems. We will continue to adapt more systems in the future.

### 1. Model Deployment

This project supports using provider APIs or locally deployed LLMs. If you need local deployment, please use OpenAI-compatible API services. We recommend using vLLM for deployment. Please refer to the [official tutorial](https://qwen.readthedocs.io/en/latest/deployment/vllm.html#openai-compatible-api-service).

### 2. Server Configuration and Startup

The following operations should be performed on the computer to be controlled.

#### 2.1 Clone Repository

```bash
git clone https://github.com/GML-FMGroup/cappuccino.git
cd cappuccino
```

#### 2.2 Install Dependencies

First install uv (skip if already installed):

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or use pip
pip install uv
```

Then install project dependencies:

```bash
uv sync
```

#### 2.3 Adjust Configuration

```bash
cp env.example .env
```

Fill in the corresponding model configuration, and adjust Agent configuration and service startup type as needed.

For Telegram settings, please refer to the TELEGRAM_SETUP.md documentation.

#### 2.4 Start Service

```bash
uv run python run_server.py
```

### 3. Send Instructions

#### Method 1: Python Script

Run the request_demo file

```bash
uv run python request_demo.py
```

Note: Run on another device to initiate network requests. Of course, you can also run it on the controlled terminal, but we recommend using another device to send instructions to avoid affecting the computer's operation execution.

#### Method 2: Telegram

Please refer to the TELEGRAM_SETUP.md documentation for details.

### ⚠️ Notes

- When selecting a model, please ensure the name is correct and the provider supports that model.
- Our current interface is implemented based on the openai library. Please ensure the provider or local deployment supports the provided model.
- Due to the instability of model output, if the run fails, try running it again or modify the question.
