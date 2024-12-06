from PIL import Image
import time
import pystray
from box import Box
import keyboard
from openai import OpenAI
import os
import tkinter as tk
from tkinter import messagebox
import pyautogui
from dotenv import load_dotenv
import re
import pyperclip
import webbrowser
import json
import yaml
import sys

load_dotenv()

conf = Box.from_yaml(filename="./config.yaml", Loader=yaml.FullLoader)


if not (os.getenv("OPENAI_API_KEY") or conf['OPENAI_API_KEY']):
    temp_root = tk.Tk()
    temp_root.withdraw()
    messagebox.showerror("Error", "Missing OpenAI API Key. Please set it in your environment variables or config.yaml.")

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY") or conf['OPENAI_API_KEY'],
)

# AI Called Functions


def open_link(url):
    webbrowser.open(url)
    return "Link opened: " + url


window_width = conf["command_bar_width"]
window_height = conf["command_bar_height"]

screen_width, screen_height = pyautogui.size()

ai_model = conf["ai_model"]
ai_max_tokens = conf["ai_max_tokens"]

messages = list(conf["preset_messages"])

# AI Stuff

tools = [
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
    }
]

# Function Stuff


def create_tray_icon():
    print("Creating Tray Icon...")
    icon_image = Image.open("./assets/tray_icon.png")
    icon = pystray.Icon("Nova Bot", icon_image, "Nova Bot")

    def stop_script():
        print("Exiting application...")
        keyboard.unhook_all()
        icon.stop()  # Gracefully stops the tray icon
        os._exit(0)  # Terminates the program without raising SystemExit

    # Assign the menu to the tray icon
    icon.menu = pystray.Menu(
        pystray.MenuItem('Exit', stop_script)
    )

    icon.run()


def entry_ctrl_bs(event):
    ent = event.widget
    end_idx = ent.index(tk.INSERT)
    start_idx = ent.get().rfind(" ", None, end_idx)
    ent.selection_range(start_idx, end_idx)


def single_prompt(prompt):
    messages.append(
        {"role": "user", "content": prompt}
    )
    """Returns response text and code blocks from OpenAI API completion"""
    response = client.chat.completions.create(
        model=ai_model,
        max_tokens=ai_max_tokens,
        messages=messages,
        tools=tools,
    )

    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls

    if tool_calls:
        messages.append(response_message)

        available_functions = {
            'open_link': open_link,
        }

        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_to_call = available_functions.get(function_name)

            if function_to_call:
                function_args = json.loads(tool_call.function.arguments)
                if function_name == 'open_link' and 'url' in function_args:
                    function_response = function_to_call(url=function_args['url'])
                else:
                    function_response = "Error: Invalid function call or missing required arguments."

                # Ensure `function_response` is always a string
                if function_response is None:
                    function_response = "The requested action was performed successfully."

                messages.append(
                    {
                        'tool_call_id': tool_call.id,
                        'role': 'tool',
                        'name': function_name,
                        'content': str(function_response),
                    }
                )

        response_2 = client.chat.completions.create(
            model=ai_model,
            messages=messages,
        )

        return response_2.choices[0].message.content.strip(), None

    messages.append(response_message)
    response_text = response_message.content.strip()

    if "```" in response_text:
        remove_cb_language = re.sub(r"(?<=```)(.*)(?=\n)", "", response_text)
        code_blocks = re.findall(r"(?<=```\n)([\s\S]*?)(?=\n```)(?=\n)", remove_cb_language)
        replace_text = re.sub(r"(```.*)", "", response_text)

        return replace_text, code_blocks

    return response_text, None


def main():

    root = tk.Tk()
    root.withdraw()
    root.title("Nova Bot")
    root.resizable(False, False)
    root.configure(padx=5, pady=5, background="black")
    root.overrideredirect(True)

    # Create widgets

    window_pos = "+" + str(round(screen_width / 2 - 0.5 * window_width)) + "+" + str(round(screen_height / 2 - 0.5 * window_height))
    root.geometry(window_pos)
    root.geometry(str(window_width) + "x" + str(window_height))

    entry_frame = tk.Frame(root, background="black")
    entry_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    root.columnconfigure(0, weight=1)

    entry_container = tk.Frame(entry_frame, background="#131313")
    entry_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

    entry = tk.Entry(entry_container, background=entry_container.cget("bg"), foreground="white", insertbackground="white", borderwidth=0)
    entry.bind("<Control-BackSpace>", entry_ctrl_bs)
    entry.pack(fill=tk.BOTH, expand=True, padx=5)

    root.update()
    entry.configure(font=f"Arial {str(entry.winfo_height() - 20)}")

    # Create functions

    def hide_window(event=None):
        root.withdraw()

    def show_window(event=None):
        root.deiconify()
        root.lift()
        root.focus_force()
        root.after(50, lambda *args: entry.focus_set())  # type: ignore

    root.bind("<FocusOut>", hide_window)
    root.bind("<Escape>", hide_window)

    hide_window()

    keyboard.add_hotkey("ctrl+shift+m", show_window, suppress=True, trigger_on_release=True)

    output_label = tk.Label(root, background="black", foreground="white", wraplength=window_width - 20)

    def entry_submit(event=None):

        global messages
        nonlocal output_label

        entry_text = entry.get().strip()
        entry.delete(0, tk.END)

        # Check for commands
        if entry_text == "/exit":
            root.destroy()
            keyboard.unhook_all()
            sys.exit()
        elif entry_text == "/clrmsg":
            messages = list(conf["preset_messages"])
            output_label.destroy()
            output_label = tk.Label(root, background="black", foreground="white", wraplength=window_width - 20)

            root.update()
            root.geometry(str(window_width) + "x" + str(window_height))
            return

        ai_response, code_blocks = single_prompt(entry_text)

        if code_blocks:
            print(code_blocks[0])
            pyperclip.copy(code_blocks[0])
            output_label.config(text=ai_response + "\n<copied text to clipboard>")
        else:
            print(ai_response)
            output_label.config(text=ai_response)

        output_label.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True, padx=(0, 5))

        root.update()
        root.geometry(str(window_width) + "x" + str(window_height + output_label.winfo_reqheight() + 20))

    button = tk.Button(entry_frame, text="Run", command=entry_submit, background=entry_container.cget("bg"), foreground="white", borderwidth=0, width=5)
    button.pack(side=tk.LEFT, fill=tk.Y)

    entry.bind("<Return>", entry_submit)

    root.mainloop()


if __name__ == '__main__':
    # create_tray_icon()
    main()

try:
    while True:
        pass
except KeyboardInterrupt:
    keyboard.unhook_all()
    sys.exit()
