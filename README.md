<div align="center">
<h1><span style="font-size: 60px;">☕️</span> cappuccino</h1>
<p><a href="./README_CN.md">中文</a> | English</p>
<p>A local automated intelligent agent that frees your hands 🤖</p>
<p>Entrust your tasks to me, and enjoy a rich cup of cappuccino ☕️</p>
<p>By the time you return, your tasks will be silently completed 🍃</p>
</div>

## 💡 Overview

**Cappuccino** is a GUI Agent that can control your computer to solve tedious tasks with a simple instruction. AI will generate detailed task plans and execute them. Unlike other existing solutions that parse image elements or use browser interfaces, **cappuccino** is a purely visual solution based on desktop screens, as we believe the parsing process easily loses spatial association information.

You can use the API directly to get started quickly or deploy LLM on local servers for greater security. Send control instructions through Python scripts or visual interface: [cappuccino-client](https://github.com/GML-FMGroup/cappuccino-client) 🖥️.

## ✨ Features

- **Local Deployment:** Each part of our architecture provides open-source model options for local deployment, with information transmission through local LAN to protect your privacy.
- **Easy to Use:** We provide a React-based GUI Client to control the Agent, which is beginner-friendly.

## 🤔 Future Work

We will support more models, optimize the agent's performance, and work on developing our own small-parameter LLM to reduce deployment costs and improve running speed.

We hope more people will pay attention to our project or join us. We will further enrich our system, create a Manus-like product suitable for local deployment, and adapt to more software operations.

Your star🌟 will be the biggest motivation for us to update!

## 📰 Update

- **[2025/03/19]** 🧠 The system architecture was upgraded to enable more complex tasks.
- **[2025/03/09]** 🖥️ We introduced cappuccino-client for easier command initiation.
- **[2025/03/04]** 💥 Deepseek-v3 is now supported as a planner.
- **[2025/02/27]** 🏆 Now you can experience cappuccino with qwen and gpt-4o.

## 🎥 Demo

https://github.com/user-attachments/assets/18b6013a-6d45-44d3-bd09-b0b08e0cd2c8

## 👨‍💻 Quickstart

### 0. Hardware preparation

At present, the project supports the deployment of Windows and Mac. Due to the differences in the shortcut keys and operation methods of the system, the experience of different systems may be different. We will carry out more system adaptation in the future.

### 1. Model Deployment

This project supports using vendor APIs or locally deploying LLMs. If you need local deployment, please use an OpenAI-compatible API service. We recommend using vLLM for deployment, referring to the [official tutorial](https://qwen.readthedocs.io/en/latest/deployment/vllm.html#openai-compatible-api-service).

For model selection, we recommend using deepseek-v3 as the planner, qwen-vl-max as the dispatcher & validator, and qwen2.5-vl-7b as the executor.

### 2. Server Configuration and Startup

The following operations are performed on the computer you want to control.

#### 2.1 Clone the Repository

```bash
git clone https://github.com/GML-FMGroup/cappuccino.git
cd cappuccino
```
#### 2.2 Install Dependencies

```bash
pip install -r requirements.txt
```

#### 2.3 Start the Server

```bash
cd app
python server.py
```
You will see your **local IP** and randomly generated **token** in the console. In this example, IP is 192.168.0.100
```bash
Generated token: 854616
Chat WebSocket: ws://192.168.0.100:8000/chat
Screenshots WebSocket: ws://192.168.0.100:8001/screenshots
```

### 3. Send Instructions

Run on another device to initiate network requests. Of course, you can also run it on the controlled terminal, but our design philosophy is to use another device to send instructions to avoid affecting the computer's operations.

#### Method 1: Python Scripts

1. Modify the IP and token in `request_demo.py`. For example, IP is 192.168.0.100.
2. Fill in LLM configuration information like API Key, vendor, etc.
3. Run the Python file.
```bash
python request_demo.py
```

#### Method 2: GUI Client

You can find a more detailed tutorial on using the GUI Client in [cappuccino-client](https://github.com/GML-FMGroup/cappuccino-client) 🖥️.

## 📖 Guide

### Design Architecture

We divide **Cappuccino** into three parts: **Model, Server, Client**.

- **Model:** You can choose to use vendors like dashscope, openai, or a more secure local deployment.
- **Server:** GUI Agent deployed on the controlled computer, enables websocket network service to receive instructions from LAN, and combines desktop screenshots with model interaction so the model can output execution instructions or plans.
- **Client:** Used to send human instructions to the server through GUI Interface or Python Scripts.

For the design of GUI Agent, we mainly divide it into four parts: **🧠Planner, 🤖Dispatcher, ✍️Executor, 🔍Verifier**.

- 🧠**Planner:** Breaks down complex user instructions into multiple tasks for step-by-step execution.
- 🤖**Dispatcher:** Combines desktop screen and executor functionality to break tasks into multiple subtasks, each being an atomic operation (the smallest unit of human computer control actions, such as: click xx, type xx).
- ✍️**Executor:** Combines desktop screen to generate parameters for script execution based on atomic operations.
- 🔍**Verifier:** Determines whether corresponding tasks have been completed based on desktop screen.

### Supported Models

| Planner - API       | Planner - Local    | Dispatcher & Verifier - API | Dispatcher & Verifier - Local | Executor - API      | Executor - Local    |
|---------------------|--------------------|-----------------------------|-------------------------------|--------------------|--------------------|
| qwen-vl-max         | deepseek-v3        | qwen-vl-max                 | qwen2.5-vl-72b                | qwen2.5-vl-7b      | qwen2.5-vl-7b      |
| gpt-4o              |                    | gpt-4o                      |                               |                    |                    |
| deepseek-v3         |                    |                             |                               |                    |                    |

### ⚠️ Notice

- Please ensure the model name is correct and the vendor supports the model when making your selection.
- Our current interface is implemented based on the openai library. Please ensure the provider or local deployment supports the provided models.
- Due to the inherent instability in model outputs, if execution fails, try running again or modifying your query.
