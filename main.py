from openai import OpenAI
from dotenv import load_dotenv
import os
import tkinter as tk

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
)


def main():
    root = tk.Tk()

    label = tk.Label(root, text="Welcome to Nova-Bot")
    label.pack()

    root.mainloop()


if __name__ == '__main__':
    main()
