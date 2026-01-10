# main.py
import sys
import os
import shutil
import tempfile
import random
from pathlib import Path
import time
import ctypes

# ============================================================================
# 🛡️ KRITICKÁ FIXACE PRO PYINSTALLER UPDATE (BOOTLOADER FIX)
# ============================================================================
# Pokud aplikace startuje po update procesu, musíme zajistit, že nevidí
# staré proměnné prostředí, které by ji navedly do smazané složky Temp.
if "_MEIPASS2" in os.environ:
    os.environ.pop("_MEIPASS2", None)

# ============================================================================
# SAFE BOOT (Záloha prostředí)
# ============================================================================
# Tento blok se snaží zachránit situaci, pokud DLL nelze najít, zkopírováním
# aktuálního prostředí. Běží pouze v zkompilovaném EXE (frozen).
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    try:
        current_mei = Path(sys._MEIPASS)
        # Unikátní název pro tuto relaci, aby se nekolidovalo
        safe_mei_path = Path(tempfile.gettempdir()) / f"AIWinget_Safe_MEI_{random.randint(1000, 99999)}"
        
        # Kopírujeme pouze pokud ještě neexistuje (rychlost)
        if not safe_mei_path.exists():
            shutil.copytree(current_mei, safe_mei_path, dirs_exist_ok=True)
            
        # Přidáme do PATH, aby Windows našel DLL pokud selže standardní cesta
        os.environ["PATH"] += os.pathsep + str(safe_mei_path)
    except Exception:
        # Pokud se záloha nepovede (např. práva), ignorujeme to a doufáme, že bootloader funguje
        pass

# ============================================================================
# HLAVNÍ APLIKACE
# ============================================================================

import tkinter as tk
import threading
from PIL import Image, ImageTk 
from config import COLORS
from splash import SplashScreen
from views import InstallerPage, UpdaterPage, PlaceholderPage, HealthCheckPage, SettingsPage
from utils import SettingsManager
from updater import CURRENT_VERSION, GitHubUpdater

def resource_path(relative_path):
    """Získá absolutní cestu ke zdrojům, funguje pro dev i pro PyInstaller"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

class MainApplication(tk.Tk):
    def __init__(self):
        super().__init__()
        self.withdraw() # Skryjeme okno během načítání
        self.title("AI Winget Installer")
        
        # Nastavení AppID pro hlavní panel Windows (aby se ikona neshlukovala s Pythonem)
        try:
            myappid = 'mycompany.aiwinget.installer.v4'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass

        # Načtení ikony okna
        try:
            image_path = resource_path("program_icon.png")
            if os.path.exists(image_path):
                original_image = Image.open(image_path)
                window_icon = ImageTk.PhotoImage(original_image)
                self.iconphoto(True, window_icon)
                # Uložíme si malou verzi pro UI
                resized_image = original_image.resize((32, 32), Image.Resampling.LANCZOS)
                self.app_icon = ImageTk.PhotoImage(resized_image)
        except Exception as e:
            # Pokud ikona chybí, nevadí, použije se defaultní
            pass

        # Geometrie okna
        w = 1175
        h = 750
        ws = self.winfo_screenwidth()
        hs = self.winfo_screenheight()
        x = int((ws/2) - (w/2))
        y = int((hs/2) - (h/2))
        self.geometry(f'{w}x{h}+{x}+{y}')

        self.configure(bg=COLORS['bg_main'])

        # Dark Mode Title Bar (Windows 10/11 hack)
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
        except Exception:
            pass

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
        profile_frame = tk.Frame(self.sidebar, bg=COLORS['bg_sidebar'], pady=20, padx=15)
        profile_frame.pack(fill='x', side="top")
        
        icon_size = 36
        cv = tk.Canvas(profile_frame, width=icon_size, height=icon_size, bg=COLORS['bg_sidebar'], highlightthickness=0)
        cv.pack(side="left")
        
        user_color = "#555555"
        cv.create_oval(8, 2, 28, 22, fill=user_color, outline="")
        cv.create_arc(2, 20, 34, 50, start=0, extent=180, fill=user_color, outline="")

        lbl_user = tk.Label(profile_frame, text="Uživatel", font=("Segoe UI", 11, "bold"), 
                            bg=COLORS['bg_sidebar'], fg=COLORS['fg'], cursor="hand2")
        lbl_user.pack(side="left", padx=12)
        
        def go_to_settings(e):
            self.switch_view("settings")

        lbl_user.bind("<Button-1>", go_to_settings)
        cv.bind("<Button-1>", go_to_settings) 
        cv.config(cursor="hand2")

        def on_user_enter(e): 
            lbl_user.config(fg=COLORS['accent']) 
        def on_user_leave(e): 
            lbl_user.config(fg=COLORS['fg'])     
            
        lbl_user.bind("<Enter>", on_user_enter)
        lbl_user.bind("<Leave>", on_user_leave)

        tk.Frame(self.sidebar, bg=COLORS['border'], height=1).pack(fill='x', padx=15, pady=(10, 20))

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
        
        tk.Label(self.sidebar, text="Moje Projekty", font=("Segoe UI", 9, "bold"), bg=COLORS['bg_sidebar'], fg=COLORS['sub_text']).pack(anchor="w", padx=20, pady=(0, 10))
        self.create_project_item("#  Winget Tools", 12)
        self.create_project_item("#  Gaming", 5)

        # CONTENT AREA
        self.content_area = tk.Frame(container, bg=COLORS['bg_main'])
        self.content_area.grid(row=0, column=1, sticky="nsew")
        
        # VIEWS
        self.views = {}
        self.views["installer"] = InstallerPage(self.content_area, self)
        self.views["updater"] = UpdaterPage(self.content_area, self)
        self.views["health"] = HealthCheckPage(self.content_area, self)
        self.views["upcoming"] = PlaceholderPage(self.content_area, "Upcoming Updates", "📅")
        self.views["settings"] = SettingsPage(self.content_area, self)
        self.views["all_apps"] = PlaceholderPage(self.content_area, "Všechny aplikace", "☰")

        self.current_view = None
        self.switch_view("installer")
        
        # Spuštění Splash Screen a následná kontrola update
        SplashScreen(self, on_complete=self.run_startup_update_check)

    def run_startup_update_check(self):
            # Kontrola update na pozadí po načtení UI
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
        
        for v in self.views.values():
            v.pack_forget()
        
        if view_name in self.views:
            self.views[view_name].pack(fill='both', expand=True)

if __name__ == "__main__":
    app = MainApplication()
    app.mainloop()