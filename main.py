# main.py
import tkinter as tk
import threading
import os
import ctypes
from PIL import Image, ImageTk 

# 1. BOOT CHECK (Musí být první)
import boot_system
boot_system.perform_boot_checks()

# 2. KONFIGURACE A UTILS
from config import COLORS, CURRENT_VERSION
from splash import SplashScreen
from updater import GitHubUpdater

# 3. NAČTENÍ POHLEDŮ (VIEWS)
from view_installer import InstallerPage
from view_health import HealthCheckPage
from view_settings import SettingsPage
from view_other import UpdaterPage, PlaceholderPage

class MainApplication(tk.Tk):
    def __init__(self):
        super().__init__()
        self.withdraw() 
        self.title("AI Winget Installer")
        
        try:
            myappid = 'mycompany.aiwinget.installer.v4'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception: pass

        try:
            image_path = boot_system.resource_path("program_icon.png")
            if os.path.exists(image_path):
                original_image = Image.open(image_path)
                window_icon = ImageTk.PhotoImage(original_image)
                self.iconphoto(True, window_icon)
                resized_image = original_image.resize((32, 32), Image.Resampling.LANCZOS)
                self.app_icon = ImageTk.PhotoImage(resized_image)
        except Exception: pass

        w, h = 1175, 750
        ws, hs = self.winfo_screenwidth(), self.winfo_screenheight()
        x, y = int((ws/2) - (w/2)), int((hs/2) - (h/2))
        self.geometry(f'{w}x{h}+{x}+{y}')
        self.configure(bg=COLORS['bg_main'])

        # Dark Mode Title Bar
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
            windll.dwmapi.DwmSetWindowAttribute(hwnd, 35, byref(c_int(hex_to_colorref(target_color))), 4)
            windll.dwmapi.DwmSetWindowAttribute(hwnd, 36, byref(c_int(hex_to_colorref("#ffffff"))), 4)
            windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, byref(c_int(1)), 4)
        except Exception: pass

        # --- LAYOUT ---
        container = tk.Frame(self, bg=COLORS['bg_main'])
        container.pack(fill='both', expand=True)
        container.grid_columnconfigure(0, weight=0, minsize=250) 
        container.grid_columnconfigure(1, weight=1)              
        container.grid_rowconfigure(0, weight=1)

        # SIDEBAR
        self.sidebar = tk.Frame(container, bg=COLORS['bg_sidebar'])
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        ver_label = tk.Label(self.sidebar, text=f"Alpha version {CURRENT_VERSION}", font=("Segoe UI", 8), bg=COLORS['bg_sidebar'], fg=COLORS['sub_text'])
        ver_label.pack(side="bottom", pady=20)

        # PROFIL
        profile_frame = tk.Frame(self.sidebar, bg=COLORS['bg_sidebar'], pady=20, padx=15, cursor="hand2")
        profile_frame.pack(fill='x', side="top")
        
        icon_size = 36
        cv = tk.Canvas(profile_frame, width=icon_size, height=icon_size, bg=COLORS['bg_sidebar'], highlightthickness=0, cursor="hand2")
        cv.pack(side="left")
        
        # Původní šedá barva ikony
        default_user_color = "#555555"
        
        # Vytvoření ikonky (panáčka)
        cv.create_oval(8, 2, 28, 22, fill=default_user_color, outline="")
        cv.create_arc(2, 20, 34, 50, start=0, extent=180, fill=default_user_color, outline="")

        lbl_user = tk.Label(profile_frame, text="Uživatel", font=("Segoe UI", 11, "bold"), 
                            bg=COLORS['bg_sidebar'], fg=COLORS['fg'], cursor="hand2")
        lbl_user.pack(side="left", padx=12)
        
        # Funkce pro kliknutí (přechod do nastavení)
        def go_to_settings(e):
            self.switch_view("settings")

        # Funkce pro Hover efekt (najetí myši)
        def on_profile_enter(e): 
            lbl_user.config(fg=COLORS['accent'])           # Změní text na modrou
            cv.itemconfig("all", fill=COLORS['accent'])    # Změní ikonku na modrou

        def on_profile_leave(e): 
            lbl_user.config(fg=COLORS['fg'])               # Vrátí bílý text
            cv.itemconfig("all", fill=default_user_color)  # Vrátí šedou ikonku

        # Aplikujeme logiku na všechny prvky v rámečku, aby to reagovalo hezky jako celek
        for widget in [profile_frame, cv, lbl_user]:
            widget.bind("<Button-1>", go_to_settings)
            widget.bind("<Enter>", on_profile_enter)
            widget.bind("<Leave>", on_profile_leave)

        # MENU
        self.menu_buttons = {}
        tk.Button(self.sidebar, text="☰  Všechny aplikace", command=lambda: self.switch_view("all_apps"),
                  bg=COLORS['accent'], fg="white", font=("Segoe UI", 10, "bold"), 
                  relief="flat", anchor="w", padx=15, pady=8, cursor="hand2").pack(fill='x', padx=15, pady=(0, 5))
        
        self.create_menu_item("installer", "📦  Installer")
        self.create_menu_item("updater", "🔄  Updater")
        self.create_menu_item("health", "🩺  Health Check")
        self.create_menu_item("upcoming", "📅  Upcoming")
        
        tk.Frame(self.sidebar, bg=COLORS['border'], height=1).pack(fill='x', padx=15, pady=20)
        

        # CONTENT AREA
        self.content_area = tk.Frame(container, bg=COLORS['bg_main'])
        self.content_area.grid(row=0, column=1, sticky="nsew")
        
        self.views = {}
        self.views["installer"] = InstallerPage(self.content_area, self)
        self.views["updater"] = UpdaterPage(self.content_area, self)
        self.views["health"] = HealthCheckPage(self.content_area, self)
        self.views["upcoming"] = PlaceholderPage(self.content_area, "Upcoming Updates", "📅")
        self.views["settings"] = SettingsPage(self.content_area, self)
        self.views["all_apps"] = PlaceholderPage(self.content_area, "Všechny aplikace", "☰")

        self.current_view = None
        self.switch_view("installer")
        
        SplashScreen(self, on_complete=self.run_startup_update_check)

    def run_startup_update_check(self):
            updater = GitHubUpdater(self)
            threading.Thread(target=lambda: updater.check_for_updates(silent=True, on_continue=self.deiconify), daemon=True).start()
    
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
        
        for v in self.views.values(): v.pack_forget()
        if view_name in self.views: self.views[view_name].pack(fill='both', expand=True)

if __name__ == "__main__":
    app = MainApplication()
    app.mainloop()