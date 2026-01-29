import json
import base64
import pyautogui
import os

def capture_screen(run_folder):
    # 检查文件夹是否存在，如果不存在则创建
    if not os.path.exists(run_folder):
        os.makedirs(run_folder)
    path = os.path.join(run_folder, 'screenshot.png')
    # 截取整个屏幕
    screenshot = pyautogui.screenshot()
    # 截图尺寸与屏幕尺寸可能不一致，需要调整截图大小以适应屏幕
    screenshot = screenshot.resize(pyautogui.size())
    # 保存截图
    screenshot.save(path)
    return path

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")
    
def get_base64_screenshot(run_folder):
    path = capture_screen(run_folder)
    base64_screenshot = encode_image(path)
    return base64_screenshot

