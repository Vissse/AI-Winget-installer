# view_other.py
import tkinter as tk
from config import COLORS

class UpdaterPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=COLORS['bg_main'])
        self.controller = controller
        center_frame = tk.Frame(self, bg=COLORS['bg_main'])
        center_frame.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(center_frame, text="🔄", font=("Segoe UI Emoji", 48), bg=COLORS['bg_main'], fg=COLORS['sub_text']).pack(pady=(0, 20))
        tk.Label(center_frame, text="Vítejte v Updater", font=("Segoe UI", 18, "bold"), bg=COLORS['bg_main'], fg="white").pack()
        tk.Label(center_frame, text="Vyberte akci z menu vlevo", font=("Segoe UI", 10), bg=COLORS['bg_main'], fg=COLORS['sub_text']).pack(pady=(5, 20))

class PlaceholderPage(tk.Frame):
    def __init__(self, parent, title, icon_emoji="✨"):
        super().__init__(parent, bg=COLORS['bg_main'])
        center_frame = tk.Frame(self, bg=COLORS['bg_main'])
        center_frame.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(center_frame, text=icon_emoji, font=("Segoe UI Emoji", 48), bg=COLORS['bg_main']).pack(pady=(0, 20))
        tk.Label(center_frame, text=f"Vítejte v {title}", font=("Segoe UI", 18, "bold"), bg=COLORS['bg_main'], fg="white").pack()
        tk.Label(center_frame, text="Vyberte akci z menu vlevo", font=("Segoe UI", 10), bg=COLORS['bg_main'], fg=COLORS['sub_text']).pack(pady=(5, 20))