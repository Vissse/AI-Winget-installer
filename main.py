# main.py
import tkinter as tk
import google.generativeai as genai
from config import COLORS, API_KEY
from splash import SplashScreen
from views import InstallerPage, UpdaterPage, PlaceholderPage

# Konfigurace AI
genai.configure(api_key=API_KEY)

class MainApplication(tk.Tk):
    def __init__(self):
        super().__init__()
        self.withdraw() 
        self.title("AI Winget Installer")
        
        w = 1175
        h = 750
        ws = self.winfo_screenwidth()
        hs = self.winfo_screenheight()
        x = int((ws/2) - (w/2))
        y = int((hs/2) - (h/2))
        self.geometry(f'{w}x{h}+{x}+{y}')

        self.configure(bg=COLORS['bg_main'])

        # VYNUCENÍ BARVY LIŠTY (Windows)
        try:
            from ctypes import windll, byref, c_int
            self.update() 
            hwnd = windll.user32.GetParent(self.winfo_id())
            def hex_to_colorref(hex_str):
                clean_hex = hex_str.lstrip('#')
                r = int(clean_hex[0:2], 16)
                g = int(clean_hex[2:4], 16)
                b = int(clean_hex[4:6], 16)
                return b | (g << 8) | (r << 16)
            target_color = COLORS['bg_sidebar'] 
            title_color_ref = hex_to_colorref(target_color)
            text_color_ref = hex_to_colorref("#ffffff")
            windll.dwmapi.DwmSetWindowAttribute(hwnd, 35, byref(c_int(title_color_ref)), 4)
            windll.dwmapi.DwmSetWindowAttribute(hwnd, 36, byref(c_int(text_color_ref)), 4)
            windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, byref(c_int(1)), 4)
        except Exception as e:
            print(f"Nepodařilo se obarvit lištu: {e}")

        # GRID ROZLOŽENÍ
        container = tk.Frame(self, bg=COLORS['bg_main'])
        container.pack(fill='both', expand=True)
        container.grid_columnconfigure(0, weight=0, minsize=250) 
        container.grid_columnconfigure(1, weight=1)              
        container.grid_rowconfigure(0, weight=1)

        # SIDEBAR
        self.sidebar = tk.Frame(container, bg=COLORS['bg_sidebar'])
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        ver_label = tk.Label(self.sidebar, text="Alpha version 4.0", font=("Segoe UI", 8), bg=COLORS['bg_sidebar'], fg=COLORS['sub_text'])
        ver_label.pack(side="bottom", pady=20)

        profile_frame = tk.Frame(self.sidebar, bg=COLORS['bg_sidebar'], pady=20, padx=15)
        profile_frame.pack(fill='x', side="top")
        cv = tk.Canvas(profile_frame, width=32, height=32, bg=COLORS['bg_sidebar'], highlightthickness=0)
        cv.pack(side="left")
        cv.create_oval(2, 2, 30, 30, fill="#555", outline="")
        cv.create_text(16, 16, text="U", fill="white", font=("Segoe UI", 12, "bold"))
        tk.Label(profile_frame, text="Uživatel", font=("Segoe UI", 11, "bold"), bg=COLORS['bg_sidebar'], fg=COLORS['fg']).pack(side="left", padx=10)
        
        self.menu_buttons = {}
        tk.Button(self.sidebar, text="☰  Všechny aplikace", command=lambda: self.switch_view("all_apps"),
                  bg=COLORS['accent'], fg="white", font=("Segoe UI", 10, "bold"), 
                  relief="flat", anchor="w", padx=15, pady=8, cursor="hand2").pack(fill='x', padx=15, pady=(0, 20))

        self.create_menu_item("installer", "📦  Installer")
        self.create_menu_item("updater", "🔄  Updater")
        self.create_menu_item("upcoming", "📅  Upcoming")
        
        tk.Frame(self.sidebar, bg=COLORS['border'], height=1).pack(fill='x', padx=15, pady=20)
        
        tk.Label(self.sidebar, text="Moje Projekty", font=("Segoe UI", 9, "bold"), bg=COLORS['bg_sidebar'], fg=COLORS['sub_text']).pack(anchor="w", padx=20, pady=(0, 10))
        self.create_project_item("#  Winget Tools", 12)
        self.create_project_item("#  Gaming", 5)

        # CONTENT AREA
        self.content_area = tk.Frame(container, bg=COLORS['bg_main'])
        self.content_area.grid(row=0, column=1, sticky="nsew")
        
        self.views = {}
        self.views["installer"] = InstallerPage(self.content_area, self)
        self.views["updater"] = UpdaterPage(self.content_area, self)
        self.views["upcoming"] = PlaceholderPage(self.content_area, "Upcoming Updates", "📅")

        self.current_view = None
        self.switch_view("installer")
        
        SplashScreen(self)

    def create_menu_item(self, view_name, text):
        btn = tk.Button(self.sidebar, text=text, font=("Segoe UI", 10), 
                        bg=COLORS['bg_sidebar'], fg=COLORS['fg'], 
                        activebackground=COLORS['sidebar_active'], activeforeground=COLORS['fg'],
                        relief="flat", anchor="w", padx=20, pady=6, cursor="hand2", bd=0)
        btn.pack(fill='x', padx=5, pady=1)
        btn.config(command=lambda: self.switch_view(view_name))
        self.menu_buttons[view_name] = btn
        btn.bind("<Enter>", lambda e: self.on_menu_hover(view_name, True))
        btn.bind("<Leave>", lambda e: self.on_menu_hover(view_name, False))

    def create_project_item(self, text, count):
        frame = tk.Frame(self.sidebar, bg=COLORS['bg_sidebar'], cursor="hand2")
        frame.pack(fill='x', padx=5, pady=1)
        lbl_text = tk.Label(frame, text=text, font=("Segoe UI", 10), bg=COLORS['bg_sidebar'], fg="#aaa", anchor="w")
        lbl_text.pack(side="left", padx=15, pady=6)
        lbl_count = tk.Label(frame, text=str(count), font=("Segoe UI", 9), bg=COLORS['bg_sidebar'], fg="#666")
        lbl_count.pack(side="right", padx=10)
        def enter(e): frame.config(bg=COLORS['sidebar_hover'])
        def leave(e): frame.config(bg=COLORS['bg_sidebar'])
        frame.bind("<Enter>", enter)
        frame.bind("<Leave>", leave)

    def on_menu_hover(self, view_name, is_hovering):
        if self.current_view == view_name: return 
        btn = self.menu_buttons[view_name]
        btn.config(bg=COLORS['sidebar_hover'] if is_hovering else COLORS['bg_sidebar'])

    def switch_view(self, view_name):
        self.current_view = view_name
        for name, btn in self.menu_buttons.items():
            if name == view_name:
                btn.config(bg=COLORS['sidebar_active'], fg=COLORS['accent'], font=("Segoe UI", 10, "bold"))
            else:
                btn.config(bg=COLORS['bg_sidebar'], fg=COLORS['fg'], font=("Segoe UI", 10,))
        for v in self.views.values():
            v.pack_forget()
        if view_name in self.views:
            self.views[view_name].pack(fill='both', expand=True)

if __name__ == "__main__":
    app = MainApplication()
    app.mainloop()