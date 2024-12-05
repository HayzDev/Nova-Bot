from PIL import Image, ImageTk
import keyboard
from openai import OpenAI
import os
import tkinter as tk
import pyautogui
from dotenv import load_dotenv
import re
import pyperclip

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
)

window_width = 800
window_height = 50

screen_width, screen_height = pyautogui.size()

ai_model = "gpt-4o"
ai_max_tokens = 5000

def entry_ctrl_bs(event):
    ent = event.widget
    end_idx = ent.index(tk.INSERT)
    start_idx = ent.get().rfind(" ", None, end_idx)
    ent.selection_range(start_idx, end_idx)

def single_prompt(prompt):
    """Returns response text and code blocks from OpenAI API completion"""
    response = client.chat.completions.create(
        model=ai_model,
        max_tokens=ai_max_tokens,
        messages=[
            {"role": "system", "content": "You are a helpful AI assistant."},
            {"role": "user", "content": prompt},
        ]
    )

    response_text = response.choices[0].message.content.strip()

    if "```" in response_text:

        remove_cb_language = re.sub(r"(?<=```)(.*)(?=\n)", "", response_text)
        code_blocks = re.findall(r"(?<=```\n)([\s\S]*?)(?=\n```)(?=\n)", remove_cb_language)
        replace_text = re.sub(r"(```.*)(?=\n)", "", response_text)

        return replace_text, code_blocks

    return response_text, None


def main():
    root = tk.Tk()
    root.title("Nova Bot")
    root.resizable(False, False)
    root.configure(padx=5, pady=5, background="black")
    root.overrideredirect(True)

    root.bind("<FocusOut>", lambda x: root.destroy())
    root.bind("<Escape>", lambda x: root.destroy())

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
    entry.focus_set()

    root.update()
    entry.configure(font=f"Arial {str(entry.winfo_height() - 20)}")

    output_label = tk.Label(root, background="black", foreground="white")

    def entry_submit(event=None):
        entry_text = entry.get().strip()
        entry.delete(0, tk.END)

        # Check for commands
        if entry_text == "/exit":
            root.destroy()
            return

        ai_response, code_blocks = single_prompt(entry_text)

        if code_blocks:
            print(code_blocks[0])
            pyperclip.copy(code_blocks[0])
        else:
            print(ai_response)

        output_label.config(text=ai_response)
        output_label.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True, padx=(0, 5))

        root.update()
        print(output_label.winfo_reqheight())
        root.geometry(str(window_width) + "x" + str(window_height + output_label.winfo_reqheight() + 20))

    button = tk.Button(entry_frame, text="Run", command=entry_submit, background=entry_container.cget("bg"), foreground="white", borderwidth=0, width=5)
    button.pack(side=tk.LEFT, fill=tk.Y)

    entry.bind("<Return>", entry_submit)

    root.mainloop()


# if __name__ == '__main__':
#     main()

keyboard.add_hotkey("ctrl+shift+m", main, suppress=True, trigger_on_release=True)
while True:
    pass