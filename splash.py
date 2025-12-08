# splash.py
import tkinter as tk
from tkinter import ttk
import random
from config import COLORS

class SplashScreen(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Načítání...")
        w, h = 450, 280
        ws, hs = self.winfo_screenwidth(), self.winfo_screenheight()
        x, y = (ws/2) - (w/2), (hs/2) - (h/2)
        self.geometry('%dx%d+%d+%d' % (w, h, x, y))
        self.overrideredirect(True) 
        self.configure(bg=COLORS['bg_main'])
        
        main_frame = tk.Frame(self, bg=COLORS['bg_main'], highlightbackground=COLORS['accent'], highlightthickness=2)
        main_frame.pack(fill='both', expand=True)

        tk.Label(main_frame, text="AI Winget Installer", font=("Segoe UI", 22, "bold"), bg=COLORS['bg_main'], fg=COLORS['fg']).pack(pady=(50, 5))
        tk.Label(main_frame, text="Alpha version 4.0", font=("Segoe UI", 10), bg=COLORS['bg_main'], fg=COLORS['accent']).pack(pady=(0, 40))

        self.loading_label = tk.Label(main_frame, text="Inicializace...", font=("Segoe UI", 9), bg=COLORS['bg_main'], fg=COLORS['sub_text'])
        self.loading_label.pack(pady=(0, 5))

        style = ttk.Style()
        style.theme_use('default')
        style.configure("Splash.Horizontal.TProgressbar", background=COLORS['accent'], troughcolor=COLORS['bg_sidebar'], borderwidth=0, thickness=6)
        
        self.progress = ttk.Progressbar(main_frame, orient="horizontal", length=350, mode="determinate", style="Splash.Horizontal.TProgressbar")
        self.progress.pack()

        self.progress_val = 0
        self.loading_steps = ["Načítání konfigurace...", "Připojování k AI...", "Kontrola Winget...", "GUI...", "Hotovo!"]
        self.step_index = 0
        self.after(100, self.animate)

    def animate(self):
        if self.progress_val < 100:
            increment = random.randint(1, 4)
            self.progress_val += increment
            self.progress['value'] = self.progress_val
            if self.progress_val > 20 and self.step_index == 0:
                self.step_index = 1
                self.loading_label.config(text=self.loading_steps[1])
            elif self.progress_val > 50 and self.step_index == 1:
                self.step_index = 2
                self.loading_label.config(text=self.loading_steps[2])
            elif self.progress_val > 80 and self.step_index == 2:
                self.step_index = 3
                self.loading_label.config(text=self.loading_steps[3])
            self.after(30, self.animate)
        else:
            self.loading_label.config(text=self.loading_steps[4])
            self.after(500, self.close_splash)

    def close_splash(self):
        self.destroy()
        self.master.deiconify()