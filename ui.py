"""User interface module that contains user interface class"""

import tkinter as tk
import multiprocessing


class UI:
    """User interface class that handles drawing labels on the screen during gameplay.
    On macOS we use a transparent tkinter window."""

    def __init__(self, message_queue: multiprocessing.Queue) -> None:
        self.champ_text: str = UI.rgb_convert((255, 255, 255))
        self.transparent: str = UI.rgb_convert((0, 0, 0))
        self.label_container: list = []
        self.message_queue = message_queue
        self.root = tk.Tk()
        self.setup_window_size()
        self.root.overrideredirect(True)
        self.root.config(bg='black')
        self.root.attributes("-alpha", 0.85)
        self.root.wm_attributes("-topmost", True)
        try:
            self.root.attributes('-transparent', True)
            self.root.config(bg='systemTransparent')
            self.transparent = 'systemTransparent'
        except tk.TclError:
            pass
        self.root.resizable(False, False)

    @classmethod
    def rgb_convert(cls, rgb: tuple) -> str:
        """Turns tuple rgb value into string for use by the UI"""
        return "#%02x%02x%02x" % rgb

    def setup_window_size(self) -> None:
        """Setups window size using screen dimensions from tkinter itself"""
        w = self.root.winfo_screenwidth()
        h = self.root.winfo_screenheight()
        self.root.geometry(f'{w}x{h}')

    def consume_text(self) -> None:
        """Consumes UI changes from the message queue"""
        if not self.message_queue.empty():
            message = self.message_queue.get()
            if 'CLEAR' in message:
                for label in self.label_container:
                    label.destroy()
                self.label_container.clear()
            else:
                for labels in message[1]:
                    label = tk.Label(self.root, text=f"{labels[0]}",
                                     bg=self.transparent, fg=self.champ_text,
                                     font=("Helvetica", 13), bd=0)
                    label.place(x=labels[1][0] - 15, y=labels[1][1] + 30)
                    self.label_container.append(label)

        self.root.after(ms=1, func=self.consume_text)

    def ui_loop(self) -> None:
        """Loop that runs indefinitely to process UI changes"""
        self.consume_text()
        self.root.mainloop()
