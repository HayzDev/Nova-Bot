from openai import OpenAI
from dotenv import load_dotenv
import os
import tkinter as tk
import pyautogui

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
)

window_width = 800
window_height = 100

screen_width, screen_height = pyautogui.size()

pyautogui.moveTo(screen_width / 2, screen_height / 2)


def main():
    root = tk.Tk()

    window_pos = "+" + str(round(screen_width / 2 - 0.5 * window_width)) + "+" + str(round(screen_height / 2 - 0.5 * window_height))
    root.geometry(window_pos)
    root.geometry(str(window_width) + "x" + str(window_height))

    entry_frame = tk.Frame(root)
    entry_frame.grid(column=0, row=0)

    entry = tk.Entry(entry_frame)
    entry.grid(column=0, row=0)

    def entry_submit(event=None):
        print("Test")

    entry.bind("<Return>", entry_submit)

    button = tk.Button(entry_frame, text="Start", command=entry_submit, borderwidth=1)
    button.grid(column=1, row=0)

    root.mainloop()


if __name__ == '__main__':
    main()
