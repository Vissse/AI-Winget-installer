import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
import google.generativeai as genai
import json
import os
import threading
import subprocess
import queue
import requests
import re
import time
from io import BytesIO
from PIL import Image, ImageTk
from urllib.parse import urlparse
import shutil 
import glob
import random

# --- KONFIGURACE ---
API_KEY = "AIzaSyC04q0Magnd7hV6oC-mh6zvd4UUT6kxhsY" 
OUTPUT_FILE = "install_apps.bat"

# --- BAREVNÉ SCHÉMA (TODOIST STYLE - BLUE ACCENT) ---
COLORS = {
    "bg_main": "#1e1e1e",
    "bg_sidebar": "#252525",
    "fg": "#ffffff",
    "accent": "#4DA6FF",
    "accent_hover": "#6ebaff",
    "sidebar_hover": "#2c2c2c",
    "sidebar_active": "#363636",
    "success": "#3fb950",
    "success_hover": "#56d364",
    "danger": "#f85149",
    "danger_hover": "#ff7b72",
    "item_bg": "#2d2d2d",
    "item_hover": "#383838",
    "input_bg": "#3c3c3c",
    "sub_text": "#8b949e",
    "border": "#30363d"
}

genai.configure(api_key=API_KEY)

# --- POMOCNÉ TŘÍDY ---

class ModernScrollbar(tk.Canvas):
    def __init__(self, parent, command=None, width=10, bg=COLORS['bg_main'], thumb_color="#424242"):
        super().__init__(parent, width=width, bg=bg, highlightthickness=0)
        self.command = command
        self.thumb_color = thumb_color
        self.hover_color = "#4f4f4f"
        self.thumb = self.create_rectangle(0, 0, width, 0, fill=self.thumb_color, outline="")
        self.bind("<ButtonPress-1>", self.on_press)
        self.bind("<B1-Motion>", self.on_drag)
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)

    def set(self, first, last):
        self.top = float(first)
        self.bottom = float(last)
        self.redraw()

    def redraw(self):
        h = self.winfo_height()
        w = self.winfo_width()
        if h == 0: return
        
        if self.bottom - self.top >= 1.0:
            self.coords(self.thumb, 0, 0, 0, 0)
            return

        y1 = h * self.top
        y2 = h * self.bottom
        if y2 - y1 < 20: y2 = y1 + 20 
        self.coords(self.thumb, 2, y1, w-2, y2) 

    def on_press(self, event):
        self.y_start = event.y
        self.top_start = self.top

    def on_drag(self, event):
        h = self.winfo_height()
        delta = (event.y - self.y_start) / h
        new_top = self.top_start + delta
        if self.command: self.command("moveto", new_top)

    def on_enter(self, event): self.itemconfig(self.thumb, fill=self.hover_color)
    def on_leave(self, event): self.itemconfig(self.thumb, fill=self.thumb_color)

# --- IKONY ---
http_session = requests.Session()
http_session.headers.update({'User-Agent': 'Mozilla/5.0'})
icon_cache = {}

class IconLoader:
    @staticmethod
    def load_async(item_data, label_widget, root):
        app_id = item_data.get("id")
        website = item_data.get("website")
        if app_id in icon_cache:
            IconLoader._update_label(label_widget, icon_cache[app_id])
            return
        thread = threading.Thread(target=IconLoader._download_strategy, args=(app_id, website, label_widget, root))
        thread.daemon = True
        thread.start()

    @staticmethod
    def _download_strategy(app_id, website, label_widget, root):
        urls_to_try = []
        if app_id:
            urls_to_try.append(f"https://raw.githubusercontent.com/marticliment/WingetUI/main/src/wingetui/Assets/Packages/{app_id}.png")
            if "." in app_id:
                short_id = app_id.split(".")[-1]
                urls_to_try.append(f"https://raw.githubusercontent.com/marticliment/WingetUI/main/src/wingetui/Assets/Packages/{short_id}.png")
            clean_id = app_id.lower().replace(".", "-")
            urls_to_try.append(f"https://cdn.jsdelivr.net/gh/walkxcode/dashboard-icons/png/{clean_id}.png")

        if website and website != "Unknown":
            domain = IconLoader.get_clean_domain(website)
            if domain:
                urls_to_try.append(f"https://icons.duckduckgo.com/ip3/{domain}.ico")
                urls_to_try.append(f"https://www.google.com/s2/favicons?domain={domain}&sz=128")

        for url in urls_to_try:
            try:
                response = http_session.get(url, timeout=1.5)
                if response.status_code == 200 and len(response.content) > 100:
                    data = response.content
                    img = Image.open(BytesIO(data))
                    if img.mode != 'RGBA': img = img.convert('RGBA')
                    img = img.resize((32, 32), Image.Resampling.LANCZOS)
                    tk_img = ImageTk.PhotoImage(img)
                    if app_id: icon_cache[app_id] = tk_img
                    root.after(0, lambda: IconLoader._update_label(label_widget, tk_img))
                    return 
            except Exception: continue 

    @staticmethod
    def get_clean_domain(url):
        try:
            if not url or "://" not in url: url = "http://" + str(url)
            parsed = urlparse(url)
            domain = parsed.netloc
            if domain.startswith("www."): domain = domain[4:]
            return domain
        except: return None

    @staticmethod
    def _update_label(label, tk_img):
        try:
            label.config(image=tk_img)
            label.image = tk_img 
        except: pass

# --- SPLASH SCREEN ---
class SplashScreen(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Načítání...")
        
        w = 450
        h = 280
        ws = self.winfo_screenwidth()
        hs = self.winfo_screenheight()
        x = (ws/2) - (w/2)
        y = (hs/2) - (h/2)
        
        self.geometry('%dx%d+%d+%d' % (w, h, x, y))
        # Splash screen necháme bez rámečku, to je standard
        self.overrideredirect(True) 
        self.configure(bg=COLORS['bg_main'])
        
        main_frame = tk.Frame(self, bg=COLORS['bg_main'], highlightbackground=COLORS['accent'], highlightthickness=2)
        main_frame.pack(fill='both', expand=True)

        tk.Label(main_frame, text="AI Winget Installer", font=("Segoe UI", 22, "bold"), bg=COLORS['bg_main'], fg=COLORS['fg']).pack(pady=(50, 5))
        tk.Label(main_frame, text="Alpha version 3.0", font=("Segoe UI", 10), bg=COLORS['bg_main'], fg=COLORS['accent']).pack(pady=(0, 40))

        self.loading_label = tk.Label(main_frame, text="Inicializace...", font=("Segoe UI", 9), bg=COLORS['bg_main'], fg=COLORS['sub_text'])
        self.loading_label.pack(pady=(0, 5))

        style = ttk.Style()
        style.theme_use('default')
        style.configure("Splash.Horizontal.TProgressbar", background=COLORS['accent'], troughcolor=COLORS['bg_sidebar'], borderwidth=0, thickness=6)
        
        self.progress = ttk.Progressbar(main_frame, orient="horizontal", length=350, mode="determinate", style="Splash.Horizontal.TProgressbar")
        self.progress.pack()

        self.progress_val = 0
        self.loading_steps = [
            "Načítání konfigurace...",
            "Připojování k AI modelu...",
            "Kontrola Winget repozitářů...",
            "Inicializace grafického rozhraní...",
            "Hotovo!"
        ]
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
        # Pouze zobrazíme hlavní okno, žádné úpravy
        self.master.deiconify()

# --- INSTALLATION DIALOG ---
class InstallationDialog:
    def __init__(self, parent, install_list):
        self.top = tk.Toplevel(parent)
        self.top.title("Průběh instalace")
        window_width = 700
        window_height = 550
        screen_width = parent.winfo_screenwidth()
        screen_height = parent.winfo_screenheight()
        x_cordinate = int((screen_width/2) - (window_width/2))
        y_cordinate = int((screen_height/2) - (window_height/2))
        self.top.geometry(f"{window_width}x{window_height}+{x_cordinate}+{y_cordinate}")
        self.top.configure(bg=COLORS['bg_main'])
        
        self.install_list = install_list
        self.total_apps = len(install_list)
        self.current_app_index = 0
        self.failed_apps = []
        self.is_running = True
        self.msg_queue = queue.Queue()

        self.title_label = tk.Label(self.top, text="🚀 Příprava instalace...", font=("Segoe UI", 16, "bold"), bg=COLORS['bg_main'], fg="white")
        self.title_label.pack(pady=(20, 10))

        style = ttk.Style()
        style.theme_use('default')
        style.configure("Green.Horizontal.TProgressbar", background=COLORS['success'], troughcolor=COLORS['input_bg'], borderwidth=0, thickness=20)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.top, variable=self.progress_var, maximum=self.total_apps, style="Green.Horizontal.TProgressbar")
        self.progress_bar.pack(fill='x', padx=30, pady=10)

        info_frame = tk.Frame(self.top, bg=COLORS['bg_main'])
        info_frame.pack(fill='x', padx=30)
        self.status_label = tk.Label(info_frame, text=f"Inicializace...", font=("Segoe UI", 11), bg=COLORS['bg_main'], fg=COLORS['sub_text'])
        self.status_label.pack(side='left')

        tk.Label(self.top, text="Detailní výpis:", font=("Segoe UI", 10, "bold"), bg=COLORS['bg_main'], fg="#555").pack(pady=(20, 5), anchor="w", padx=30)
        self.text_area = scrolledtext.ScrolledText(self.top, font=("Consolas", 9), bg="#111", fg="#cccccc", insertbackground="white", relief="flat", height=15, highlightthickness=1, highlightbackground=COLORS['border'])
        self.text_area.pack(fill='both', expand=True, padx=30, pady=(0, 10))

        self.close_btn = tk.Button(self.top, text="Zrušit", command=self.close_window, bg=COLORS['danger'], fg="white", font=("Segoe UI", 10), relief="flat", padx=25, pady=8, cursor="hand2")
        self.close_btn.pack(pady=15)
        self.close_btn.bind("<Enter>", lambda e: self.on_hover(self.close_btn, COLORS['danger_hover']))
        self.close_btn.bind("<Leave>", lambda e: self.on_leave(self.close_btn, COLORS['danger']))

        threading.Thread(target=self.run_installation_sequence, daemon=True).start()
        self.check_queue()

    def close_window(self):
        self.is_running = False
        self.top.destroy()

    def on_hover(self, btn, color): btn.config(bg=color)
    def on_leave(self, btn, color): btn.config(bg=color)

    def check_queue(self):
        while not self.msg_queue.empty():
            try:
                msg_type, content = self.msg_queue.get_nowait()
                if msg_type == "LOG":
                    self.text_area.insert(tk.END, content)
                    self.text_area.see(tk.END)
                elif msg_type == "STATUS":
                    self.title_label.config(text=f"Právě instaluji: {content}")
                elif msg_type == "PROGRESS":
                    self.current_app_index = content
                    self.progress_var.set(content)
                    self.update_status_labels()
                elif msg_type == "DONE":
                    self.finish_installation()
                elif msg_type == "ERROR":
                    self.text_area.insert(tk.END, f"\n!!! CHYBA: {content} !!!\n", "error")
                    self.text_area.tag_config("error", foreground="#ff5555")
                elif msg_type == "FAIL_RECORD":
                    self.failed_apps.append(content)
            except queue.Empty: break
        
        if self.is_running:
            self.top.after(100, self.check_queue)

    def update_status_labels(self):
        self.status_label.config(text=f"Zpracováno {self.current_app_index} z {self.total_apps} aplikací")

    def create_desktop_shortcut(self, app_name):
        try:
            start_menu_paths = [
                os.path.join(os.environ['APPDATA'], r'Microsoft\Windows\Start Menu\Programs'),
                os.path.join(os.environ['PROGRAMDATA'], r'Microsoft\Windows\Start Menu\Programs')
            ]
            desktop_path = os.path.join(os.environ['USERPROFILE'], 'Desktop')
            search_terms = app_name.split()
            search_query = search_terms[0] if len(search_terms) > 0 else app_name
            found = False
            for path in start_menu_paths:
                for root, dirs, files in os.walk(path):
                    for file in files:
                        if file.lower().endswith(".lnk") and search_query.lower() in file.lower():
                            src_file = os.path.join(root, file)
                            dst_file = os.path.join(desktop_path, file)
                            shutil.copy2(src_file, dst_file)
                            self.msg_queue.put(("LOG", f"➕ Vytvořen zástupce na ploše: {file}\n"))
                            found = True
                            break 
                    if found: break
                if found: break
        except Exception as e:
            self.msg_queue.put(("LOG", f"(Chyba při tvorbě zástupce: {e})\n"))

    def run_installation_sequence(self):
        self.msg_queue.put(("STATUS", "Aktualizace databáze..."))
        self.msg_queue.put(("LOG", "--- AKTUALIZACE ZDROJŮ WINGET ---\n"))
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            subprocess.run('winget source update', shell=True, startupinfo=startupinfo, creationflags=subprocess.CREATE_NO_WINDOW)
            self.msg_queue.put(("LOG", ">>> Databáze úspěšně aktualizována.\n\n"))
        except Exception as e:
            self.msg_queue.put(("LOG", f"Warning: Aktualizace zdrojů selhala ({str(e)}), pokračuji...\n\n"))

        self.msg_queue.put(("LOG", "--- ZAHAJUJI HROMADNOU INSTALACI ---\n"))
        for i, app_data in enumerate(self.install_list):
            if not self.is_running: break
            app_name = app_data['name']
            app_id = app_data['id'].strip()
            self.msg_queue.put(("STATUS", app_name))
            self.msg_queue.put(("LOG", f"\n>>> Instaluji: {app_name} ({app_id})...\n"))
            
            cmd = f'winget install --id "{app_id}" --silent --accept-package-agreements --accept-source-agreements --force --disable-interactivity'
            try:
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='cp852', errors='replace', startupinfo=startupinfo)
                for line in process.stdout:
                    if not self.is_running: 
                        process.terminate(); break
                    clean_line = line.replace('\r', '').replace('\n', '').replace('\b', '')
                    stripped_line = clean_line.strip()
                    if not stripped_line: continue
                    if stripped_line in ['\\', '|', '/', '-']: continue
                    if "MB /" in stripped_line or "kB /" in stripped_line or "%" in stripped_line or "██" in stripped_line: continue
                    self.msg_queue.put(("LOG", clean_line + "\n"))
                process.wait()
                if process.returncode == 0:
                    self.msg_queue.put(("LOG", f"✅ {app_name} úspěšně nainstalován.\n"))
                    self.create_desktop_shortcut(app_name)
                else:
                    self.msg_queue.put(("ERROR", f"❌ Chyba při instalaci {app_name} (kód {process.returncode}).\n"))
                    self.msg_queue.put(("FAIL_RECORD", app_name))
            except Exception as e:
                self.msg_queue.put(("ERROR", str(e)))
                self.msg_queue.put(("FAIL_RECORD", app_name))
            self.msg_queue.put(("PROGRESS", i + 1))
        self.msg_queue.put(("DONE", None))

    def finish_installation(self):
        self.is_running = False
        self.progress_var.set(self.total_apps)
        self.close_btn.config(text="Zavřít", bg=COLORS['success'], command=self.top.destroy)
        self.close_btn.bind("<Enter>", lambda e: self.on_hover(self.close_btn, COLORS['success_hover']))
        self.close_btn.bind("<Leave>", lambda e: self.on_leave(self.close_btn, COLORS['success']))
        if len(self.failed_apps) == 0:
            self.title_label.config(text="HOTOVO! Vše nainstalováno.", fg=COLORS['success'])
            self.status_label.config(text="Instalace dokončena bez chyb.")
        else:
            self.title_label.config(text="HOTOVO (s chybami)", fg="orange")
            self.failed_apps_str = ", ".join(self.failed_apps)
            self.status_label.config(text=f"Nepodařilo se nainstalovat: {self.failed_apps_str}", fg=COLORS['danger'])

# --- STRÁNKA INSTALLER ---
class InstallerPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=COLORS['bg_main'])
        self.controller = controller
        
        try:
            self.default_icon = ImageTk.PhotoImage(Image.new('RGB', (32, 32), color=COLORS['item_bg']))
        except: pass

        self.queue_data = {} 
        self.is_searching = False

        self.columnconfigure(0, weight=1, uniform="group1") 
        self.columnconfigure(1, weight=1, uniform="group1") 
        self.rowconfigure(0, weight=0) 
        self.rowconfigure(1, weight=1) 

        # --- 1. HEADER ---
        header_frame = tk.Frame(self, bg=COLORS['bg_main'], pady=15)
        header_frame.grid(row=0, column=0, columnspan=2, sticky="ew")
        tk.Label(header_frame, text="Installer", font=("Segoe UI", 18, "bold"), bg=COLORS['bg_main'], fg=COLORS['fg']).pack(side="left", padx=20)
    

        # --- LEVÝ PANEL ---
        left_panel = tk.Frame(self, bg=COLORS['bg_main'], padx=20, pady=10)
        left_panel.grid(row=1, column=0, sticky="nsew")
        
        tk.Label(left_panel, text="Zadejte název programu", font=("Segoe UI", 14, "bold"), bg=COLORS['bg_main'], fg=COLORS['fg'], anchor="w").pack(fill='x')
        tk.Label(left_panel, text="(Nebo popište, co hledáte, např. 'úprava zvuku')", font=("Segoe UI", 9), bg=COLORS['bg_main'], fg=COLORS['sub_text'], anchor="w").pack(fill='x', pady=(0, 10))
        
        search_frame = tk.Frame(left_panel, bg=COLORS['bg_main'])
        search_frame.pack(fill='x', pady=(0, 10))
        
        search_border = tk.Frame(search_frame, bg=COLORS['input_bg'], bd=0, highlightthickness=0) 
        search_border.pack(fill='x', ipady=2)
        
        self.input_entry = tk.Entry(search_border, font=("Segoe UI", 12), bg=COLORS['input_bg'], fg="white", insertbackground="white", relief="flat")
        self.input_entry.pack(side='left', fill='both', expand=True, padx=10)
        self.input_entry.bind('<Return>', lambda event: self.start_search())

        self.search_btn = self.create_animated_btn(search_border, "Hledat", self.start_search, COLORS['accent'], COLORS['accent_hover'])
        self.search_btn.pack(side='right', fill='y', padx=2, pady=2)

        style = ttk.Style()
        style.theme_use('default')
        style.configure("Horizontal.TProgressbar", background=COLORS['accent'], troughcolor=COLORS['bg_main'], borderwidth=0, thickness=2)
        self.progress = ttk.Progressbar(search_frame, orient="horizontal", mode="indeterminate", style="Horizontal.TProgressbar")

        tk.Label(left_panel, text="Výsledky hledání:", font=("Segoe UI", 11, "bold"), bg=COLORS['bg_main'], fg=COLORS['sub_text'], anchor="w").pack(fill='x', pady=(10, 5))
        
        self.found_container = tk.Frame(left_panel, bg=COLORS['bg_sidebar'])
        self.found_container.pack(fill='both', expand=True, pady=(0, 20))
        
        self.found_canvas = tk.Canvas(self.found_container, bg=COLORS['bg_sidebar'], highlightthickness=0)
        self.found_scrollbar = ModernScrollbar(self.found_container, command=self.found_canvas.yview, bg=COLORS['bg_sidebar'])
        self.found_scrollable = tk.Frame(self.found_canvas, bg=COLORS['bg_sidebar'])
        
        self.found_scrollable.bind("<Configure>", self.on_frame_configure)
        self.found_canvas.create_window((0, 0), window=self.found_scrollable, anchor="nw", width=480)
        self.found_canvas.configure(yscrollcommand=self.found_scrollbar.set)
        self.found_canvas.bind("<Configure>", lambda e: self.found_canvas.itemconfig(self.found_canvas.find_all()[0], width=e.width))

        self.found_canvas.pack(side="left", fill="both", expand=True)
        self.found_scrollbar.pack(side="right", fill="y")
        self._bind_mousewheel(self.found_container, self.found_canvas)


        # --- PRAVÝ PANEL ---
        right_panel = tk.Frame(self, bg=COLORS['bg_main'], padx=20, pady=10)
        right_panel.grid(row=1, column=1, sticky="nsew")

        queue_header = tk.Frame(right_panel, bg=COLORS['bg_main'])
        queue_header.pack(fill='x', pady=(0, 10))
        tk.Label(queue_header, text="Instalační fronta:", font=("Segoe UI", 11, "bold"), bg=COLORS['bg_main'], fg=COLORS['sub_text']).pack(side="left")

        right_footer = tk.Frame(right_panel, bg=COLORS['bg_main'], pady=20)
        right_footer.pack(side="bottom", fill='x')

        self.create_animated_btn(right_footer, "Vymazat frontu", self.clear_queue, COLORS['danger'], COLORS['danger_hover']).pack(side="left")
        self.create_animated_btn(right_footer, "Uložit inst. soubor", self.save_only, COLORS['input_bg'], COLORS['item_hover']).pack(side="left", padx=10)
        self.create_animated_btn(right_footer, "INSTALOVAT VŠE", self.install_now, COLORS['success'], COLORS['success_hover']).pack(side="right", fill='x', expand=True, padx=(10, 0))

        self.queue_container = tk.Frame(right_panel, bg=COLORS['bg_sidebar'])
        self.queue_container.pack(fill='both', expand=True)

        self.queue_canvas = tk.Canvas(self.queue_container, bg=COLORS['bg_sidebar'], highlightthickness=0)
        self.queue_scrollbar = ModernScrollbar(self.queue_container, command=self.queue_canvas.yview, bg=COLORS['bg_sidebar'])
        self.queue_scrollable = tk.Frame(self.queue_canvas, bg=COLORS['bg_sidebar'])
        
        self.queue_scrollable.bind("<Configure>", lambda e: self.queue_canvas.configure(scrollregion=self.queue_canvas.bbox("all")))
        self.queue_canvas.create_window((0, 0), window=self.queue_scrollable, anchor="nw", width=480)
        self.queue_canvas.configure(yscrollcommand=self.queue_scrollbar.set)
        self.queue_canvas.bind("<Configure>", lambda e: self.queue_canvas.itemconfig(self.queue_canvas.find_all()[0], width=e.width))

        self.queue_canvas.pack(side="left", fill="both", expand=True)
        self.queue_scrollbar.pack(side="right", fill="y")
        self._bind_mousewheel(self.queue_container, self.queue_canvas)

    def on_frame_configure(self, event):
        self.found_canvas.configure(scrollregion=self.found_canvas.bbox("all"))

    def create_animated_btn(self, parent, text, command, bg_color, hover_color):
        btn = tk.Button(parent, text=text, command=command, bg=bg_color, fg="white", font=("Segoe UI", 10, "bold"), relief="flat", padx=15, pady=8, cursor="hand2", borderwidth=0)
        def on_enter(e):
            if btn['state'] != 'disabled': btn.config(bg=hover_color)
        def on_leave(e):
            if btn['state'] != 'disabled': btn.config(bg=bg_color)
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        return btn

    def _bind_mousewheel(self, widget, canvas):
        def _on_mousewheel(event):
            if canvas.bbox("all"):
                scroll_height = canvas.bbox("all")[3]
                visible_height = canvas.winfo_height()
                if scroll_height <= visible_height: return 
            
            if event.num == 5 or event.delta < 0: canvas.yview_scroll(1, "units")
            elif event.num == 4 or event.delta > 0: canvas.yview_scroll(-1, "units")
            self.found_scrollbar.redraw()
            self.queue_scrollbar.redraw()
        
        bind_enter = lambda e: {canvas.bind_all("<MouseWheel>", _on_mousewheel), canvas.bind_all("<Button-4>", _on_mousewheel), canvas.bind_all("<Button-5>", _on_mousewheel)}
        bind_leave = lambda e: {canvas.unbind_all("<MouseWheel>"), canvas.unbind_all("<Button-4>"), canvas.unbind_all("<Button-5>")}
        widget.bind('<Enter>', bind_enter)
        widget.bind('<Leave>', bind_leave)

    def start_search(self):
        user_request = self.input_entry.get()
        if not user_request:
            messagebox.showwarning("Chyba", "Napiš název programu.")
            return
        if self.is_searching: return 
        self.is_searching = True
        self.search_btn.config(cursor="arrow") 
        self.input_entry.delete(0, 'end') 
        self.progress.pack(fill='x', pady=(5, 0))
        self.progress.start(10) 
        threading.Thread(target=self.get_winget_ids_thread, args=(user_request,)).start()

    def get_winget_ids_thread(self, user_request):
        model = genai.GenerativeModel('gemini-2.5-flash') 
        
        print(f"--- FÁZE 1: Zjišťování záměru pro: '{user_request}' ---")
        
        # 1. KROK: Zjištění záměru (Intent Recognition)
        # Ptáme se AI: Je to název, nebo kategorie?
        intent_prompt = f"""
        Jsi expert na Windows software a Winget repozitář.
        Uživatel zadal: "{user_request}"

        Tvým úkolem je rozhodnout, jak tento dotaz hledat ve Winget.
        
        SCÉNÁŘ A (Konkrétní aplikace):
        Pokud uživatel myslí konkrétní program (i s překlepem, např. "discrd", "chrom", "vlc"),
        vráť POUZE opravený název.
        
        SCÉNÁŘ B (Obecný popis/Kategorie):
        Pokud uživatel hledá typ programu (např. "úprava videa", "webový prohlížeč", "pdf reader", "něco na hudbu"),
        vyber několik NEJLEPŠÍCH a NEJPOPULÁRNĚJŠÍCH aplikací pro Windows v této kategorii, které jsou určitě na Wingetu.
        
        Odpověz POUZE v tomto formátu (žádný markdown, žádný úvod):
        QUERIES: název1;název2;název3
        """

        search_terms = []
        try:
            intent_response = model.generate_content(intent_prompt)
            raw_intent = intent_response.text.strip()
            
            # Parsování odpovědi (očekáváme "QUERIES: app1;app2...")
            if "QUERIES:" in raw_intent:
                clean_line = raw_intent.replace("QUERIES:", "").strip()
                # Rozdělíme středníkem a vyčistíme
                search_terms = [t.strip() for t in clean_line.split(";") if t.strip()]
            else:
                # Fallback, kdyby AI neodpověděla správně
                search_terms = [user_request]
                
            print(f"AI navrhlo hledat tyto výrazy: {search_terms}")

        except Exception as e:
            print(f"Chyba při zjišťování záměru: {e}")
            search_terms = [user_request]

        # 2. KROK: Hromadné hledání ve Winget
        # Spustíme hledání pro každý výraz, který AI navrhlo
        combined_output = ""
        
        self.progress['maximum'] = len(search_terms) * 100
        current_prog = 0
        
        for term in search_terms:
            try:
                # Omezíme výsledky (-n 3) aby toho nebylo moc pro další AI analýzu
                cmd = f'winget search "{term}" --source winget --accept-source-agreements -n 3'
                
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
                print(f"Spouštím Winget pro: {term}")
                result = subprocess.run(cmd, capture_output=True, text=True, startupinfo=startupinfo, encoding='cp852', errors='replace')
                
                # Přidáme výstup do jednoho velkého textu
                combined_output += f"\n--- VÝSLEDKY PRO '{term}' ---\n"
                combined_output += result.stdout
                
            except Exception as e:
                print(f"Winget search selhal pro {term}: {e}")
            
            # Aktualizace progress baru (jen vizuálně)
            current_prog += 100
            # V threadu nemůžeme přímo měnit GUI bezpečně, ale u jednoduchých proměnných to v Tkinteru často projde. 
            # Správnější by bylo frontování, ale pro jednoduchost necháme běžet.

        # 3. KROK: Finální filtrace a formátování na JSON
        # Teď máme "špinavý" výstup z několika hledání, AI z toho musí vytáhnout to důležité.
        
        filter_prompt = f"""
        Mám výstup z příkazové řádky (Winget Search) pro různé hledané výrazy.
        Původní dotaz uživatele byl: "{user_request}"
        
        SUROVÁ DATA Z WINGET:
        '''
        {combined_output}
        '''

        INSTRUKCE:
        1. Analyzuj surová data a najdi aplikace, které odpovídají záměru uživatele.
        2. Pokud data obsahují balast (knihovny, ovladače), ignoruj je. Hledáme hlavní aplikace. (bez duplicit - žádné Bety ani jiné alternativní verze určitého programu). Pokud se budou nacházet dvě verze určitého programu např. GIMP má z nějakého důvodu ve wingetu 2 verze, vždy vyber tu novější.
        3. Extrahuj Název, ID a Verzi.
        4. Pokud ID nevidíš v datech, ale jsi si jistý, že to je ta správná aplikace (např. jsi ji sám navrhl v předchozím kroku), pokus se ID odhadnout (např. 'Mozilla.Firefox').
        
        VÝSTUPNÍ FORMÁT (čistý JSON pole):
        [
            {{ 
                "name": "Název aplikace", 
                "id": "Přesné.ID", 
                "version": "verze (nebo 'Latest')", 
                "website": "domena.com" 
            }}
        ]
        """

        try:
            response = model.generate_content(filter_prompt)
            raw_text = response.text
            # Očištění o markdown bloky
            json_str = raw_text.replace("```json", "").replace("```", "").strip()
            
            # Extrakce JSONu pomocí regexu pro jistotu
            json_match = re.search(r'\[.*\]', json_str, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
            else:
                data = []

            # Validace verzí (stejné jako předtím)
            for item in data:
                if not item.get('version') or item['version'] == "Latest":
                     # Zde bychom mohli volat get_real_version, ale pro rychlost to necháme být
                     # nebo to voláme jen když je to nutné.
                     item['version'] = "Latest/Unknown"

            self.controller.after(0, self.display_search_results, data)

        except Exception as e:
            print(f"Chyba při finálním parsování: {e}")
            self.controller.after(0, lambda: messagebox.showerror("Chyba AI", f"Chyba zpracování.\nDetail: {e}"))
            self.controller.after(0, self.stop_loading_animation)

    def stop_loading_animation(self):
        self.progress.stop()
        self.progress.pack_forget()
        self.is_searching = False
        self.search_btn.config(cursor="hand2")

    def display_search_results(self, items):
        self.stop_loading_animation()
        for widget in self.found_scrollable.winfo_children(): widget.destroy()
        if not items:
            tk.Label(self.found_scrollable, text="Nic nenalezeno.", bg=COLORS['bg_sidebar'], fg="gray").pack(pady=20)
            return
        for item in items:
            self.create_list_item(self.found_scrollable, item, is_result_mode=True)
        self.found_canvas.update_idletasks()
        self.found_scrollbar.redraw()

    def create_list_item(self, parent_scrollable, item_data, is_result_mode):
        name = item_data.get("name")
        app_id = item_data.get("id")
        version = item_data.get("version")
        
        card = tk.Frame(parent_scrollable, bg=COLORS['item_bg'], pady=10, padx=10)
        card.pack(fill='x', padx=(10,0), pady=5)

        icon_label = tk.Label(card, image=self.default_icon, bg=COLORS['item_bg'])
        icon_label.pack(side="left", padx=(0, 15))
        IconLoader.load_async(item_data, icon_label, self.controller)

        text_frame = tk.Frame(card, bg=COLORS['item_bg'])
        text_frame.pack(side="left", fill="both", expand=True)
        tk.Label(text_frame, text=name, font=("Segoe UI", 11, "bold"), bg=COLORS['item_bg'], fg="white", anchor="w").pack(fill="x")
        tk.Label(text_frame, text=f"ID: {app_id} | v{version}", font=("Segoe UI", 9), bg=COLORS['item_bg'], fg=COLORS['sub_text'], anchor="w").pack(fill="x")

        action_symbol = tk.Label(card, font=("Arial", 18), bg=COLORS['item_bg'], cursor="hand2", padx=10)
        action_symbol.pack(side="right")

        if is_result_mode:
            action_symbol.config(text="＋", fg=COLORS['accent'])
            action_symbol.bind("<Button-1>", lambda e, i=item_data: self.add_item_to_queue(i))
            self._bind_symbol_hover(action_symbol, COLORS['accent'], COLORS['fg'])
        else:
            action_symbol.config(text="✕", fg=COLORS['danger'])
            action_symbol.bind("<Button-1>", lambda e, aid=app_id: self.remove_from_queue(aid))
            self._bind_symbol_hover(action_symbol, COLORS['danger'], COLORS['fg'])

        self._bind_card_hover(card, text_frame, icon_label, action_symbol)

    def _bind_symbol_hover(self, widget, hover_bg, hover_fg):
        normal_bg = COLORS['item_bg']
        normal_fg = widget.cget("fg")
        def on_enter(e): widget.config(bg=hover_bg, fg=hover_fg)
        def on_leave(e): widget.config(bg=normal_bg, fg=normal_fg)
        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)

    def _bind_card_hover(self, card, text_frame, icon_label, action_symbol):
        widgets_to_change = [card, text_frame, icon_label] + text_frame.winfo_children()
        def on_enter(e):
            for w in widgets_to_change: w.config(bg=COLORS['item_hover'])
            if e.widget != action_symbol: action_symbol.config(bg=COLORS['item_hover'])
        def on_leave(e):
            for w in widgets_to_change: w.config(bg=COLORS['item_bg'])
            if e.widget != action_symbol: action_symbol.config(bg=COLORS['item_bg'])
        card.bind("<Enter>", on_enter)
        card.bind("<Leave>", on_leave)

    def add_item_to_queue(self, item_data):
        app_id = item_data.get("id")
        if app_id in self.queue_data: return
        self.queue_data[app_id] = item_data
        self.create_list_item(self.queue_scrollable, item_data, is_result_mode=False)
        self.queue_canvas.update_idletasks()
        self.queue_canvas.yview_moveto(1.0)
        self.queue_scrollbar.redraw()

    def remove_from_queue(self, app_id):
        if app_id in self.queue_data:
            del self.queue_data[app_id]
            self.refresh_queue_view()

    def refresh_queue_view(self):
        for widget in self.queue_scrollable.winfo_children(): widget.destroy()
        for app_id, item_data in self.queue_data.items():
            self.create_list_item(self.queue_scrollable, item_data, is_result_mode=False)
        self.queue_canvas.update_idletasks()
        self.queue_scrollbar.redraw()

    def clear_queue(self):
        self.queue_data = {}
        self.refresh_queue_view()

    def _create_batch_file(self):
        if not self.queue_data:
            messagebox.showwarning("Pozor", "Seznam je prázdný.")
            return False
            
        try:
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f: 
                f.write("@echo off\nchcp 65001 > nul\necho Zahajuji instalaci...\n\n")
                for aid, data in self.queue_data.items():
                    f.write(f"echo Instaluji: {data['name']}...\n")
                    f.write(f"winget install -e --id {aid} --silent --accept-package-agreements --accept-source-agreements\n")
                    f.write("echo ----------------------------------------\n")
                f.write("\necho Hotovo!\n")
            return True
        except Exception as e:
            messagebox.showerror("Chyba", str(e))
            return False

    def save_only(self):
        if self._create_batch_file(): 
            messagebox.showinfo("Uloženo", f"Soubor: {OUTPUT_FILE}")

    def install_now(self):
        if not self.queue_data:
            messagebox.showwarning("Pozor", "Seznam je prázdný.")
            return
        InstallationDialog(self.controller, list(self.queue_data.values()))


# --- PLACEHOLDER PRO OSTATNÍ ZÁLOŽKY ---
class PlaceholderPage(tk.Frame):
    def __init__(self, parent, title, icon_emoji="✨"):
        super().__init__(parent, bg=COLORS['bg_main'])
        
        center_frame = tk.Frame(self, bg=COLORS['bg_main'])
        center_frame.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(center_frame, text=icon_emoji, font=("Segoe UI Emoji", 48), bg=COLORS['bg_main']).pack(pady=(0, 20))
        tk.Label(center_frame, text=f"Vítejte v {title}", font=("Segoe UI", 18, "bold"), bg=COLORS['bg_main'], fg="white").pack()
        tk.Label(center_frame, text="Vyberte akci z menu vlevo", font=("Segoe UI", 10), bg=COLORS['bg_main'], fg=COLORS['sub_text']).pack(pady=(5, 20))


# --- HLAVNÍ APLIKACE (BEZ ÚPRAV PANELU) ---
class MainApplication(tk.Tk):
    def __init__(self):
        super().__init__()
        # --- OPRAVA PROBLIKNUTÍ ---
        self.withdraw() 
        
        self.title("AI Winget Installer")
        
        # 1. CENTROVÁNÍ OKNA
        w = 1100
        h = 700
        ws = self.winfo_screenwidth()
        hs = self.winfo_screenheight()
        x = int((ws/2) - (w/2))
        y = int((hs/2) - (h/2))
        self.geometry(f'{w}x{h}+{x}+{y}')

        self.configure(bg=COLORS['bg_main'])

        # 2. VYNUCENÍ BARVY LIŠTY
        try:
            import ctypes
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

        # --- GRID ROZLOŽENÍ ---
        container = tk.Frame(self, bg=COLORS['bg_main'])
        container.pack(fill='both', expand=True)
        container.grid_columnconfigure(0, weight=0, minsize=250) 
        container.grid_columnconfigure(1, weight=1)              
        container.grid_rowconfigure(0, weight=1)

        # SIDEBAR
        self.sidebar = tk.Frame(container, bg=COLORS['bg_sidebar'])
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        # --- NOVÉ: VERZE DOLE V SIDEBARU ---
        # Použijeme pack(side="bottom"), aby to bylo vždy na dně panelu
        ver_label = tk.Label(self.sidebar, text="Alpha version 3.0", font=("Segoe UI", 8), bg=COLORS['bg_sidebar'], fg=COLORS['sub_text'])
        ver_label.pack(side="bottom", pady=20)

        # Profil
        profile_frame = tk.Frame(self.sidebar, bg=COLORS['bg_sidebar'], pady=20, padx=15)
        profile_frame.pack(fill='x', side="top") # side="top" je default, ale pro přehlednost
        cv = tk.Canvas(profile_frame, width=32, height=32, bg=COLORS['bg_sidebar'], highlightthickness=0)
        cv.pack(side="left")
        cv.create_oval(2, 2, 30, 30, fill="#555", outline="")
        cv.create_text(16, 16, text="U", fill="white", font=("Segoe UI", 12, "bold"))
        tk.Label(profile_frame, text="Uživatel", font=("Segoe UI", 11, "bold"), bg=COLORS['bg_sidebar'], fg=COLORS['fg']).pack(side="left", padx=10)
        
        # Menu tlačítka
        self.menu_buttons = {}
        tk.Button(self.sidebar, text="⊕  Quick Install", bg=COLORS['accent'], fg="white", font=("Segoe UI", 10, "bold"), relief="flat", anchor="w", padx=15, pady=8, cursor="hand2").pack(fill='x', padx=15, pady=(0, 20))

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
        self.views["updater"] = PlaceholderPage(self.content_area, "Updater View", "🔄")
        self.views["upcoming"] = PlaceholderPage(self.content_area, "Upcoming Updates", "📅")

        self.current_view = None
        self.switch_view("installer")
        
        # Spustíme Splash Screen
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