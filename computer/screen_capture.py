import pyautogui
import os

def capture_screen():
    # 检查文件夹是否存在，如果不存在则创建
    if not os.path.exists('./temp'):
        os.makedirs('./temp')
    path = './temp/screenshot.png'
    # 截取整个屏幕
    screenshot = pyautogui.screenshot()
    # 截图尺寸与屏幕尺寸可能不一致，需要调整截图大小以适应屏幕
    screenshot = screenshot.resize(pyautogui.size())
    # 保存截图
    screenshot.save(path)
    return path
