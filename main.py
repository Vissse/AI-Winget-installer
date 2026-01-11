# main.py
import tkinter as tk
import sys
import os
import ctypes
import threading
from PIL import Image, ImageTk 

# Moduly
import boot_system
from config import COLORS, CURRENT_VERSION, THEMES
from splash import SplashScreen
from updater import GitHubUpdater

# IMPORTY
from view_installer import InstallerPage
from view_health import HealthCheckPage
from view_settings import SettingsPage
from view_other import UpdaterPage, PlaceholderPage
from view_dashboard import DashboardPage

boot_system.perform_boot_checks()

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class MainApplication(tk.Tk):
    def __init__(self):
        super().__init__()
        self.withdraw() 
        self.title("AI Winget Installer")
        
        # AppID pro správnou ikonu na taskbaru
        try:
            myappid = 'mycompany.aiwinget.installer.v6'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception: pass

        # Ikona
        try:
            image_path = resource_path("program_icon.png")
            if os.path.exists(image_path):
                original_image = Image.open(image_path)
                window_icon = ImageTk.PhotoImage(original_image)
                self.iconphoto(True, window_icon)
                resized_image = original_image.resize((32, 32), Image.Resampling.LANCZOS)
                self.app_icon = ImageTk.PhotoImage(resized_image)
        except Exception: pass

        w, h = 1175, 750
        ws, hs = self.winfo_screenwidth(), self.winfo_screenheight()
        x = int((ws/2) - (w/2))
        y = int((hs/2) - (h/2))
        self.geometry(f'{w}x{h}+{x}+{y}')

        # Hlavní kontejner
        self.container = tk.Frame(self, bg=COLORS['bg_main'])
        self.container.pack(fill='both', expand=True)
        
        # Grid konfigurace: Sloupec 0 je Sidebar (začíná na 0px), Sloupec 1 je Obsah
        self.container.grid_columnconfigure(0, weight=0, minsize=0) 
        self.container.grid_columnconfigure(1, weight=1)              
        self.container.grid_rowconfigure(0, weight=1)

        self.create_interface()
        SplashScreen(self, on_complete=self.run_startup_update_check)

    def create_interface(self):
        self.configure(bg=COLORS['bg_main'])
        self.apply_window_theme()

        # --- 1. SIDEBAR (Skrytý při startu - width=0) ---
        self.sidebar = tk.Frame(self.container, bg=COLORS['bg_sidebar'], width=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False) # Důležité: obsah neroztáhne sidebar
        self.sidebar.pack_propagate(False)

        # Obsah Sidebaru
        ver_label = tk.Label(self.sidebar, text=f"Alpha version {CURRENT_VERSION}", font=("Segoe UI", 8), bg=COLORS['bg_sidebar'], fg=COLORS['sub_text'])
        ver_label.pack(side="bottom", pady=20)

        # Profil
        self.create_profile_section()

        tk.Frame(self.sidebar, bg=COLORS['border'], height=1).pack(fill='x', padx=15, pady=(10, 20))

        # Menu tlačítka
        self.menu_buttons = {}
        
        # --- ODSTRANĚNO TLAČÍTKO DOMŮ ---
        # Nyní začínáme rovnou nástroji
        
        self.create_menu_item("installer", "📦  Installer")
        self.create_menu_item("updater", "🔄  Updater")
        self.create_menu_item("health", "🩺  Health Check")
        self.create_menu_item("upcoming", "📅  Upcoming")
        
        tk.Frame(self.sidebar, bg=COLORS['border'], height=1).pack(fill='x', padx=15, pady=20)
        
        tk.Label(self.sidebar, text="Moje Projekty", font=("Segoe UI", 9, "bold"), bg=COLORS['bg_sidebar'], fg=COLORS['sub_text']).pack(anchor="w", padx=20, pady=(0, 10))
        self.create_project_item("#  Winget Tools", 12)
        self.create_project_item("#  Gaming", 5)

        # --- 2. CONTENT AREA ---
        self.content_area = tk.Frame(self.container, bg=COLORS['bg_main'])
        self.content_area.grid(row=0, column=1, sticky="nsew")
        
        # Views
        self.views = {}
        self.views["all_apps"] = DashboardPage(self.content_area, self)
        self.views["installer"] = InstallerPage(self.content_area, self)
        self.views["updater"] = UpdaterPage(self.content_area, self)
        self.views["health"] = HealthCheckPage(self.content_area, self)
        self.views["upcoming"] = PlaceholderPage(self.content_area, "Upcoming Updates", "📅")
        self.views["settings"] = SettingsPage(self.content_area, self)

        # START NA DASHBOARDU (bez sidebaru)
        self.switch_view("all_apps", initial=True)

    def create_profile_section(self):
        profile_frame = tk.Frame(self.sidebar, bg=COLORS['bg_sidebar'], pady=20, padx=15, cursor="hand2")
        profile_frame.pack(fill='x', side="top")
        
        icon_size = 36
        cv = tk.Canvas(profile_frame, width=icon_size, height=icon_size, bg=COLORS['bg_sidebar'], highlightthickness=0, cursor="hand2")
        cv.pack(side="left")
        
        default_user_color = "#555555" if COLORS['bg_sidebar'] == "#ffffff" else "#888888"
        user_oval = cv.create_oval(8, 2, 28, 22, fill=default_user_color, outline="")
        user_arc = cv.create_arc(2, 20, 34, 50, start=0, extent=180, fill=default_user_color, outline="")

        lbl_user = tk.Label(profile_frame, text="Uživatel", font=("Segoe UI", 11, "bold"), 
                            bg=COLORS['bg_sidebar'], fg=COLORS['fg'], cursor="hand2")
        lbl_user.pack(side="left", padx=12)
        
        def go_to_settings(e): self.switch_view("settings")
        def on_enter(e): 
            lbl_user.config(fg=COLORS['accent']) 
            cv.itemconfig(user_oval, fill=COLORS['accent'])
            cv.itemconfig(user_arc, fill=COLORS['accent'])
        def on_leave(e): 
            lbl_user.config(fg=COLORS['fg'])     
            cv.itemconfig(user_oval, fill=default_user_color)
            cv.itemconfig(user_arc, fill=default_user_color)

        for w in [profile_frame, cv, lbl_user]:
            w.bind("<Button-1>", go_to_settings)
            w.bind("<Enter>", on_enter)
            w.bind("<Leave>", on_leave)

    # --- PŘEPÍNÁNÍ POHLEDŮ ---

    def open_view_from_dashboard(self, view_name):
        """Voláno z Dashboardu po kliknutí na kartu."""
        self.switch_view(view_name)

    def switch_view(self, view_name, initial=False):
        self.current_view = view_name
        
        # LOGIKA SIDEBARU
        if view_name == "all_apps":
            # Skrýt sidebar
            self.container.grid_columnconfigure(0, minsize=0)
            self.sidebar.configure(width=0)
        else:
            # Zobrazit sidebar
            self.container.grid_columnconfigure(0, minsize=250)
            self.sidebar.configure(width=250)

        # Aktualizace menu tlačítek (zvýraznění aktivního)
        for name, btn in self.menu_buttons.items():
            if name == view_name:
                btn.config(bg=COLORS['sidebar_active'], fg=COLORS['accent'], font=("Segoe UI", 10, "bold"))
            else:
                btn.config(bg=COLORS['bg_sidebar'], fg=COLORS['fg'], font=("Segoe UI", 10))
        
        # Přepnutí obsahu
        for v in self.views.values():
            v.pack_forget()
        
        if view_name in self.views:
            self.views[view_name].pack(fill='both', expand=True)

    # --- POMOCNÉ METODY ---

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
        lbl_text = tk.Label(frame, text=text, font=("Segoe UI", 10), bg=COLORS['bg_sidebar'], fg="#aaa" if COLORS['bg_sidebar']!='#ffffff' else '#666', anchor="w")
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

    def run_startup_update_check(self):
        updater = GitHubUpdater(self)
        threading.Thread(target=lambda: updater.check_for_updates(silent=True, on_continue=self.deiconify), daemon=True).start()

    def update_theme(self, theme_name):
        if theme_name in THEMES:
            COLORS.update(THEMES[theme_name])
            for widget in self.container.winfo_children(): widget.destroy()
            self.create_interface()

    def apply_window_theme(self):
        try:
            from ctypes import windll, byref, c_int
            self.update() 
            hwnd = windll.user32.GetParent(self.winfo_id())
            def hex_to_colorref(hex_str):
                clean_hex = hex_str.lstrip('#')
                r = int(clean_hex[0:2], 16); g = int(clean_hex[2:4], 16); b = int(clean_hex[4:6], 16)
                return b | (g << 8) | (r << 16)
            target_color = COLORS['bg_sidebar'] 
            text_color = "#ffffff" if COLORS['bg_sidebar'] != "#ffffff" else "#000000"
            is_dark = 1 if COLORS['bg_sidebar'] != "#ffffff" else 0
            windll.dwmapi.DwmSetWindowAttribute(hwnd, 35, byref(c_int(hex_to_colorref(target_color))), 4)
            windll.dwmapi.DwmSetWindowAttribute(hwnd, 36, byref(c_int(hex_to_colorref(text_color))), 4)
            windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, byref(c_int(is_dark)), 4)
        except: pass

if __name__ == "__main__":
    app = MainApplication()
    app.mainloop()