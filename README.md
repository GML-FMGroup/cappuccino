<h2 align="center">
    <img src="./assets/AutoMate_logo.png" alt="Logo" >
</h2>

## Overview

**AutoMate** is an agent based on desktop screenshots. You can use the API directly to get started quickly or deploy LLM on local servers for greater security.

We provide two ways to use: **planner** and **workflow**. In **planner** mode, you can enter complex instructions and let LLM help you plan the tasks of completing the instructions. In **workflow** mode, you can formulate a series of simple instructions for LLM to execute to achieve more stable results.

## Future Work

In the future, we will support more models such as deepseek, optimize the agent's performance, and also work on making our own executor model or benchmark. 

In addition, I will launch a local React-based interface in the near future to facilitate more users.

Your star🌟 will be the biggest motivation for me to update!

## Update

- **[2025/02/27]** 👨‍💻Now you can experience AutoMate with qwen.

## Quickstart

### Install Dependencies
```bash
pip install -r requirements.txt
```
### Start service
```bash
uvicorn server:server --host 0.0.0.0 --port 8000 --reload
```
You will see your **local ip**, **token** in the console.
```bash
Local IP Address: 172.16.8.34
Generated token: 111111
```
### Run demo
First, you need to modify the IP and token in the `request_demo.py` file.

Then, run the following command on another device to initiate a network request. Of course, you can also run it on the controlled terminal, but our design philosophy is to use another device to send instructions to avoid affecting the computer's execution of operations.
```bash
python request_demo.py
```
Currently, this method is temporarily used to experience Auto Mate, and we will launch a visualization platform for use in the near future.


## Guide

### Supported models
| planner  | executor   | 
|----------|------------|
| QwenVL   | Qwen2.5-VL |
