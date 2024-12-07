import tkinter as tk
from os import _exit

import keyboard
import pyautogui
import pyperclip
import threading
import sys
import os
import re
import json
import yaml
import webbrowser
from PIL import Image
import pystray
from box import Box
from openai import OpenAI
from tkinter import messagebox
from dotenv import load_dotenv


class NovaBot:
    def __init__(self):
        load_dotenv()

        with open("./config/memory.json") as f:
            self.memories = json.load(f)

        self.conf = Box.from_yaml(filename="./config/config.yaml", Loader=yaml.FullLoader)
        self.check_api_key()
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY") or self.conf['OPENAI_API_KEY'])
        
        self.window_width = self.conf["command_bar_width"]
        self.window_height = self.conf["command_bar_height"]
        self.screen_width, self.screen_height = pyautogui.size()
        self.ai_model = self.conf["ai_model"]
        self.ai_max_tokens = self.conf["ai_max_tokens"]
        self.messages = list(self.conf["preset_messages"])

        self.memory_message_content = "Your memories: "

        for memory in self.memories:
            self.memory_message_content += f"\n{memory}"

        self.memory_message = {"role": "system", "content": self.memory_message_content}

        self.messages.append(self.memory_message)

        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "open_link",
                    "description": "opens a link in the default web browser",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {"type": "string"}
                        },
                        "required": ["url"],
                        "additionalProperties": False
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "text_type",
                    "description": "types the given text",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"}
                        },
                        "required": ["text"],
                        "additionalProperties": False
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "add_memory",
                    "description": "adds a memory to the list of memories",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"}
                        },
                        "required": ["text"],
                        "additionalProperties": False
                    }
                }
            }
        ]
        
        self.root = None
        self.output_window = None
        self.entry = None
        self.output_label = None

    def check_api_key(self):
        if not (os.getenv("OPENAI_API_KEY") or self.conf['OPENAI_API_KEY']):
            temp_root = tk.Tk()
            temp_root.withdraw()
            messagebox.showerror("Error", "Missing OpenAI API Key. Please set it in your environment variables or config.yaml.")

    @staticmethod
    def open_link(url):
        webbrowser.open(url)
        return "Link opened: " + url

    def text_type(self, text):
        pyautogui.typewrite(text, self.conf['type_speed'])
        return "Text typed: " + text

    def add_memory(self, text):
        self.memories.append(text)
        with open("./config/memory.json", 'w', encoding='utf-8') as json_file:
            json.dump(self.memories, json_file, ensure_ascii=False, indent=4)

    @staticmethod
    def create_tray_icon():
        icon_image = Image.open("./assets/tray_icon.png")
        icon = pystray.Icon("Nova Bot", icon_image, "Nova Bot")

        def stop_script():
            print("Exiting application...")
            keyboard.unhook_all()
            icon.stop()
            _exit(0)

        icon.menu = pystray.Menu(pystray.MenuItem('Exit', stop_script))

        def run_icon():
            icon.run()

        icon_thread = threading.Thread(target=run_icon, daemon=True)
        icon_thread.start()

    @staticmethod
    def entry_ctrl_bs(event):
        ent = event.widget
        end_idx = ent.index(tk.INSERT)
        start_idx = ent.get().rfind(" ", None, end_idx)
        ent.selection_range(start_idx, end_idx)

    def single_prompt(self, prompt):
        self.messages.append({"role": "user", "content": prompt})
        response = self.client.chat.completions.create(
            model=self.ai_model,
            max_tokens=self.ai_max_tokens,
            messages=self.messages,
            tools=self.tools,
        )

        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls

        if tool_calls:
            self.messages.append(response_message)
            available_functions = {
                'open_link': self.open_link,
                'text_type': self.text_type,
                'add_memory': self.add_memory,
            }

            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_to_call = available_functions.get(function_name)

                if function_to_call:
                    function_response = None
                    function_args = json.loads(tool_call.function.arguments)
                    if function_name == 'open_link' and 'url' in function_args:
                        function_response = function_to_call(function_args['url'])
                    elif function_name == 'text_type' and 'text' in function_args:
                        self.root.withdraw()
                        function_response = function_to_call(function_args['text'])
                    elif function_name == 'add_memory' and 'text' in function_args:
                        function_to_call(function_args['text'])
                    else:
                        function_response = "Error: Invalid function call or missing required arguments."

                    if function_response is None:
                        function_response = "The requested action was performed successfully."

                    self.messages.append({
                        'tool_call_id': tool_call.id,
                        'role': 'tool',
                        'name': function_name,
                        'content': str(function_response),
                    })

            response_2 = self.client.chat.completions.create(
                model=self.ai_model,
                messages=self.messages,
            )

            return response_2.choices[0].message.content.strip(), None

        self.messages.append(response_message)
        response_text = response_message.content.strip()

        if "```" in response_text:
            remove_cb_language = re.sub(r"(?<=```)(.*)(?=\n)", "", response_text)
            code_blocks = re.findall(r"(?<=```\n)([\s\S]*?)(?=\n```)(?=\n)", remove_cb_language)
            replace_text = re.sub(r"(```.*)", "", response_text)
            return replace_text, code_blocks

        return response_text, None

    def setup_ui(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title("Nova Bot")
        self.root.resizable(False, False)
        self.root.configure(padx=5, pady=5, background="black")
        self.root.overrideredirect(True)

        self.output_window = tk.Toplevel(self.root)
        self.output_window.title("Output")
        self.output_window.configure(background="black", padx=5, pady=5)
        self.output_window.geometry(f"{self.window_width}x{self.window_height}")
        output_window_pos = "+" + str(round(self.screen_width / 2 - 0.5 * self.window_width)) + "+" + str(
            round((self.screen_height / 2 - 0.5 * self.window_height) + 70))
        self.output_window.geometry(output_window_pos)
        self.output_window.overrideredirect(True)
        self.output_window.withdraw()

        window_pos = "+" + str(round(self.screen_width / 2 - 0.5 * self.window_width)) + "+" + str(round(self.screen_height / 2 - 0.5 * self.window_height))
        self.root.geometry(window_pos)
        self.root.geometry(f"{self.window_width}x{self.window_height}")

        entry_frame = tk.Frame(self.root, background="black")
        entry_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.root.columnconfigure(0, weight=1)

        entry_container = tk.Frame(entry_frame, background="#131313")
        entry_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        self.entry = tk.Entry(entry_container, background=entry_container.cget("bg"), foreground="white", insertbackground="white", borderwidth=0)
        self.entry.bind("<Control-BackSpace>", self.entry_ctrl_bs)
        self.entry.pack(fill=tk.BOTH, expand=True, padx=5)

        self.root.update()
        self.entry.configure(font=f"Arial {str(self.entry.winfo_height() - 20)}")

        self.output_label = tk.Label(self.output_window, background="black", foreground="white", wraplength=self.window_width - 20)
        self.output_label.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)

        button = tk.Button(entry_frame, text="Run", command=self.entry_submit, background=entry_container.cget("bg"),
                           foreground="white", borderwidth=0, width=5)
        button.pack(side=tk.LEFT, fill=tk.Y)

        self.entry.bind("<Return>", self.entry_submit)

        self.root.bind("<FocusOut>", self.hide_window)
        self.root.bind("<Escape>", self.hide_window)

        keyboard.add_hotkey("ctrl+shift+m", self.show_window, suppress=True, trigger_on_release=True)

    def hide_window(self, event=None):
        self.root.withdraw()
        self.output_window.withdraw()

    def show_window(self, event=None):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self.root.attributes('-topmost', True)  # Make the window stay on top
        self.root.after(10, lambda: self.root.attributes('-topmost', False))  # Disable topmost after a short delay
        self.root.after(50, lambda: self.entry.focus_set())
        # Unbind the FocusOut event temporarily
        self.root.unbind("<FocusOut>")
        # Rebind the FocusOut event after a short delay
        self.root.after(100, lambda: self.root.bind("<FocusOut>", self.hide_window))

    def entry_submit(self, event=None):
        entry_text = self.entry.get().strip()
        self.entry.delete(0, tk.END)

        if entry_text == "/exit":
            self.root.destroy()
            keyboard.unhook_all()
            sys.exit()
        elif entry_text == "/clrmsg":
            self.messages = list(self.conf["preset_messages"])
            self.output_label.destroy()
            self.output_label = tk.Label(self.root, background="black", foreground="white", wraplength=self.window_width - 20)
            self.root.update()
            self.root.geometry(f"{self.window_width}x{self.window_height}")
            return

        ai_response, code_blocks = self.single_prompt(entry_text)

        self.output_window.withdraw()

        if code_blocks:
            print(code_blocks[0])
            pyperclip.copy(code_blocks[0])
            self.output_label.config(text=ai_response + "\n<copied text to clipboard>")
        else:
            print(ai_response)
            self.output_label.config(text=ai_response)

        self.output_window.deiconify()
        self.output_window.lift()
        self.output_window.update()
        self.output_window.geometry(f"{self.window_width}x{self.window_height + self.output_label.winfo_reqheight()}")

        self.output_label.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True, padx=(0, 5))

    def run(self):
        self.create_tray_icon()
        self.setup_ui()
        self.root.mainloop()

if __name__ == '__main__':
    cmd_bar = NovaBot()
    cmd_bar.run()

    try:
        while True:
            pass
    except KeyboardInterrupt:
        keyboard.unhook_all()
        sys.exit()