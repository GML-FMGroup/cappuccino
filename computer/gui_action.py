import pyautogui
import pyperclip
import os


class GuiAction:
    def __init__(self, controlledOS):
        # 屏幕操控的实际像素
        self.screen_width, self.screen_height = pyautogui.size()
        self.controlledOS = controlledOS
    
    def log_message(self, message):
        """将日志消息写入文件"""
        log_file_path = os.path.join('..', 'temp', 'gui_action.log')
        with open(log_file_path, 'a') as log_file:
            log_file.write(message + '\n')

    def perform_action(self, arguments):
        # 参数示例：
        # arguments: {"action": "left_click", "coordinate": [230, 598]}
        # arguments: {"action": "type", "text": "英雄联盟"}
        # arguments: {"action": "key", "keys": ["enter"]}
        
        if arguments["action"] == "key":
            self.key(arguments["keys"])
        elif arguments["action"] == "type":
            self.type(arguments["text"])
        elif arguments["action"] == "mouse_move":
            self.mouse_move(arguments["coordinate"][0], arguments["coordinate"][1])
        elif arguments["action"] == "left_click":
            self.left_click(arguments["coordinate"][0], arguments["coordinate"][1])
        elif arguments["action"] == "right_click":
            self.right_click(arguments["coordinate"][0], arguments["coordinate"][1])
        elif arguments["action"] == "middle_click":
            self.middle_click(arguments["coordinate"][0], arguments["coordinate"][1])


    def key(self, keys=None):
        if keys is None:
            self.log_message("key: Please provide keys.")
        else:
            pyautogui.typewrite(keys)

    def type(self, text=None):
        if text is None:
            self.log_message("type: Please provide text.")
        else:
            pyperclip.copy(text)
            if self.controlledOS == "Darwin":
                pyautogui.hotkey('command', 'v')
            else:
                pyautogui.hotkey('ctrl', 'v')

    def mouse_move(self, x=None, y=None):
        if x is None or y is None:
            self.log_message("mouse_move: Please provide x and y coordinates.")
        else:
            pyautogui.moveTo(x, y)

    def left_click(self, x=None, y=None):
        if x is None or y is None:
            self.log_message("left_click: Please provide x and y coordinates.")
            pyautogui.click()
        else:
            pyautogui.click(x, y)

    def left_click_drag(self, x=None, y=None):
        if x is None or y is None:
            self.log_message("left_click_drag: Please provide x and y coordinates.")
        else:
            pyautogui.dragTo(x, y, 0.5)

    def right_click(self, x=None, y=None):
        if x is None or y is None:
            self.log_message("right_click: Please provide x and y coordinates.")
            pyautogui.rightClick()
        else:
            pyautogui.rightClick(x, y)

    def middle_click(self, x=None, y=None):
        if x is None or y is None:
            self.log_message("middle_click: Please provide x and y coordinates.")
            pyautogui.middleClick()
        else:
            pyautogui.middleClick(x, y)

    def double_click(self, x=None, y=None):
        if x is None or y is None:
            self.log_message("double_click: Please provide x and y coordinates.")
            pyautogui.doubleClick()
        else:
            pyautogui.doubleClick(x, y)

    def scroll(self, pixels=None):
        if pixels is None:
            self.log_message("scroll: Please provide pixels.")
        else:
            pyautogui.scroll(pixels)

    def wait(self, time=None):
        if time is None:
            self.log_message("wait: Please provide time.")
        else:
            time.sleep(time)

    def terminate(self, status=None):
        if status is None:
            self.log_message("terminate: Please provide status.")
        else:
            return status
        