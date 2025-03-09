<p align="center">
    <img src="./assets/AutoMate_logo.png" alt="Logo" width="30%">
</p>

## 💡 Overview

**AutoMate** is an GUI Agent based on desktop screenshots. You can use the API directly to get started quickly or deploy LLM on local servers for greater security.

We provide two ways to use: **Planner** and **Workflow**. In **Planner** mode, you can enter complex instructions and let LLM help you plan the tasks of completing the instructions. In **Workflow** mode, you can formulate a series of simple instructions for LLM to execute to achieve more stable results.

You can use AutoMate by [AutoMate-Client](https://github.com/GML-FMGroup/AutoMate-Client) 🖥️, or use the request_demo to write scripts to call AutoMate according to your needs.

## 🤔 Future Work

In the future, we will support more models, optimize the agent's performance, and also work on making our own executor model or benchmark. 

Your star🌟 will be the biggest motivation for me to update!

## 📰 Update

- **[2025/03/09]** 🖥️ We introduced AutoMate-Client for easier initiation commands.
- **[2025/03/04]** 💥 Deepseek-v3 is now supported as a planner.
- **[2025/02/27]** 🏆 Now you can experience AutoMate with qwen and gpt-4o.

## 🎥 Demo

<img width="49%" alt="Automate_Client_Planner" src="https://github.com/user-attachments/assets/9330e712-c4dd-4a99-bd80-c69a54570c69" >
<img width="49%" alt="Automate_Client_Workflow" src="https://github.com/user-attachments/assets/c95275e7-48c0-43b9-8b84-c699cb383d0a">

https://github.com/user-attachments/assets/2effe15b-e164-46d3-a779-df391514a182

https://github.com/user-attachments/assets/9e094395-ba0e-4b6f-8d70-059b26a3c9e8

## 👨‍💻 Quickstart

### 1. Server Configuration and Startup

The following operations are performed on the computer you need to be controlled.

#### 1.1 Clone the Repository

```bash
git clone https://github.com/GML-FMGroup/AutoMate.git
cd AutoMate
```
#### 1.2 Install Dependencies

```bash
pip install -r requirements.txt
```

#### 1.3 Start the Server

```bash
python server.py
```
You will see your **local ip**, **token** in the console.
```bash
Generated token: 854616
Chat WebSocket: ws://192.168.0.100:8000/chat
Screenshots WebSocket: ws://192.168.0.100:8001/screenshots
```

### 2. Use Client

Run on another device to initiate a network request.
Of course, you can also run it on the controlled terminal, but our design philosophy is to use another device to send instructions to avoid affecting the computer's execution of operations.

#### Method 1: Python scripts

1. You need to modify the IP and token in the `request_demo.py`. For the example above, IP is 192.168.0.100
2. Fill in configuration information and query.
3. Run Python file.
```bash
python request_demo.py
```

#### Method 2: GUI Client

You can get a more detailed tutorial on using the GUI Client in [AutoMate-Client](https://github.com/GML-FMGroup/AutoMate-Client) 🖥️

## 📖 Guide

### Design concept

We divide AutoMate into three parts: **Model, Server, Client**.

- **Model:** You can choose to use vendors like dashscope, openai or a more secure local deployment.
- **Server:** This is a GUI Agent, which is deployed on a controlled computer, enables the network service to receive instructions from the LAN, and combines the desktop screenshot to the Model, so that the Model can output execution instructions or plan.
- **Client:** Used to send human instructions to server through GUI Interface or Python Scripts.

For the design of GUI Agent, we divide it into two parts: **🧠Planner and ✍️Executor**.

- 🧠**Planner:** Used to break down complex user query into simple instructions based on the current desktop screenshot.
- ✍️**Executor:** Used to generate executable instructions in combination with desktop screenshots.

Please note that when the selected Planner does not have multimodal functions, such as deepseek-v3, we use vision model to interpret desktop interpretation to help Planner better plan.

### Usage mode

- **Planner:** You can tell the LLM your needs like a conversation, so that the LLM can intelligently fulfill your needs.
- **Workflow:** You need to define a series of simple execution instructions to the LLM to obtain more precise results.

### Supported models

| Planner - API           | Planner - Local         | Executor - API          | Executor - Local        |
|-------------------------|-------------------------|-------------------------|-------------------------|
| qwen-vl-max             | deepseek-v3             | qwen2.5-vl-7b           | qwen2.5-vl-7b           |
| gpt-4o                  |                         |                         |                         |
| deepseek-v3             |                         |                         |                         |

### ⚠️ Notice

- Please make sure that the name is correct and that the supplier supports the model when selecting a model.
- Our current interface is implemented based on the openai library. Please make sure the provider or local deployment support provided.
- The Executor configuration is necessary. When you use Workflow mode, you can not fill in the Planner configuration.
