import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk, filedialog
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

# --- BAREVNÉ SCHÉMA ---
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

# --- POMOCNÉ TŘÍDY (ToolTip, Scrollbar, IconLoader, Splash) ---
# (Zde zůstávají stejné jako v předchozím kódu, pro úsporu místa je neopakuji celé, 
# ale ve finálním souboru musí být. Předpokládám, že je tam máš.)

class ToolTip(object):
    def __init__(self, widget, text='widget info'):
        self.waittime = 400     
        self.wraplength = 180   
        self.widget = widget
        self.text = text
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)
        self.widget.bind("<ButtonPress>", self.leave)
        self.id = None
        self.tw = None

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hidetip()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(self.waittime, self.showtip)

    def unschedule(self):
        id = self.id
        self.id = None
        if id:
            self.widget.after_cancel(id)

    def showtip(self, event=None):
        x = y = 0
        x, y, cx, cy = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        self.tw = tk.Toplevel(self.widget)
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry("+%d+%d" % (x, y))
        label = tk.Label(self.tw, text=self.text, justify='left',
                       background="#2d2d2d", foreground="#ffffff",
                       relief='solid', borderwidth=1,
                       font=("Segoe UI", 8, "normal"), padx=5, pady=2)
        label.pack(ipadx=1)

    def hidetip(self):
        tw = self.tw
        self.tw= None
        if tw:
            tw.destroy()

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
        
        def on_enter(e): self.close_btn.config(bg=COLORS['danger_hover'])
        def on_leave(e): self.close_btn.config(bg=COLORS['danger'])
        self.close_btn.bind("<Enter>", on_enter)
        self.close_btn.bind("<Leave>", on_leave)

        threading.Thread(target=self.run_installation_sequence, daemon=True).start()
        self.check_queue()

    def close_window(self):
        self.is_running = False
        self.top.destroy()

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
        def on_enter(e): self.close_btn.config(bg=COLORS['success_hover'])
        def on_leave(e): self.close_btn.config(bg=COLORS['success'])
        self.close_btn.bind("<Enter>", on_enter)
        self.close_btn.bind("<Leave>", on_leave)
        if len(self.failed_apps) == 0:
            self.title_label.config(text="HOTOVO! Vše nainstalováno.", fg=COLORS['success'])
            self.status_label.config(text="Instalace dokončena bez chyb.")
        else:
            self.title_label.config(text="HOTOVO (s chybami)", fg="orange")
            self.failed_apps_str = ", ".join(self.failed_apps)
            self.status_label.config(text=f"Nepodařilo se nainstalovat: {self.failed_apps_str}", fg=COLORS['danger'])

# --- NOVÁ STRÁNKA: UPDATER (SEZNAM INSTALOVANÝCH APLIKACÍ) ---
class UpdaterPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=COLORS['bg_main'])
        self.controller = controller
        
        try:
            self.default_icon = ImageTk.PhotoImage(Image.new('RGB', (32, 32), color=COLORS['item_bg']))
        except: pass

        self.upgradable_apps = [] # Seznam aplikací, které mají update

        # Header
        header_frame = tk.Frame(self, bg=COLORS['bg_main'], pady=15)
        header_frame.pack(fill='x')
        tk.Label(header_frame, text="Správce aktualizací", font=("Segoe UI", 18, "bold"), bg=COLORS['bg_main'], fg=COLORS['fg']).pack(side="left", padx=20)

        # Controls
        controls_frame = tk.Frame(self, bg=COLORS['bg_main'], padx=20)
        controls_frame.pack(fill='x', pady=(0, 10))

        self.stats_label = tk.Label(controls_frame, text="Načítám seznam aplikací...", font=("Segoe UI", 10), bg=COLORS['bg_main'], fg=COLORS['sub_text'])
        self.stats_label.pack(side="left")

        # Buttons
        btn_frame = tk.Frame(controls_frame, bg=COLORS['bg_main'])
        btn_frame.pack(side="right")

        self.refresh_btn = tk.Button(btn_frame, text="🔄 Obnovit", command=self.start_scan, bg=COLORS['input_bg'], fg="white", relief="flat", padx=15, pady=5, cursor="hand2")
        self.refresh_btn.pack(side="left", padx=5)
        
        self.update_all_btn = tk.Button(btn_frame, text="🚀 Aktualizovat vše", command=self.update_all, bg=COLORS['success'], fg="white", relief="flat", padx=15, pady=5, cursor="hand2", state="disabled")
        self.update_all_btn.pack(side="left", padx=5)

        # Progress bar
        self.progress = ttk.Progressbar(self, orient="horizontal", mode="indeterminate")
        self.progress.pack(fill='x', padx=20, pady=(0, 10))

        # List Area
        self.list_container = tk.Frame(self, bg=COLORS['bg_sidebar'])
        self.list_container.pack(fill='both', expand=True, padx=20, pady=(0, 20))
        
        self.list_canvas = tk.Canvas(self.list_container, bg=COLORS['bg_sidebar'], highlightthickness=0)
        self.list_scrollbar = ModernScrollbar(self.list_container, command=self.list_canvas.yview, bg=COLORS['bg_sidebar'])
        self.list_scrollable = tk.Frame(self.list_canvas, bg=COLORS['bg_sidebar'])
        
        self.list_scrollable.bind("<Configure>", lambda e: self.list_canvas.configure(scrollregion=self.list_canvas.bbox("all")))
        self.list_canvas.create_window((0, 0), window=self.list_scrollable, anchor="nw", width=480)
        self.list_canvas.configure(yscrollcommand=self.list_scrollbar.set)
        self.list_canvas.bind("<Configure>", lambda e: self.list_canvas.itemconfig(self.list_canvas.find_all()[0], width=e.width))

        self.list_canvas.pack(side="left", fill="both", expand=True)
        self.list_scrollbar.pack(side="right", fill="y")
        self._bind_mousewheel(self.list_container, self.list_canvas)

        # Spustit skenování při startu
        self.after(500, self.start_scan)

    def _bind_mousewheel(self, widget, canvas):
        def _on_mousewheel(event):
            if canvas.bbox("all"):
                scroll_height = canvas.bbox("all")[3]
                visible_height = canvas.winfo_height()
                if scroll_height <= visible_height: return 
            if event.num == 5 or event.delta < 0: canvas.yview_scroll(1, "units")
            elif event.num == 4 or event.delta > 0: canvas.yview_scroll(-1, "units")
            self.list_scrollbar.redraw()
        bind_enter = lambda e: {canvas.bind_all("<MouseWheel>", _on_mousewheel), canvas.bind_all("<Button-4>", _on_mousewheel), canvas.bind_all("<Button-5>", _on_mousewheel)}
        bind_leave = lambda e: {canvas.unbind_all("<MouseWheel>"), canvas.unbind_all("<Button-4>"), canvas.unbind_all("<Button-5>")}
        widget.bind('<Enter>', bind_enter)
        widget.bind('<Leave>', bind_leave)

    def start_scan(self):
        self.progress.start(10)
        self.stats_label.config(text="Prohledávám nainstalované aplikace (může to chvíli trvat)...")
        self.refresh_btn.config(state="disabled")
        self.update_all_btn.config(state="disabled")
        
        # Vyčistit list
        for widget in self.list_scrollable.winfo_children(): widget.destroy()
        
        threading.Thread(target=self.scan_thread).start()

    def scan_thread(self):
        self.upgradable_apps = []
        installed_apps = []
        
        try:
            # Spustíme 'winget list', který vrátí vše (Name, Id, Version, Available, Source)
            # Parametr --accept-source-agreements je nutný, aby se neptal
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            # Použijeme prostý výpis, protože JSON formát u 'list' je v některých verzích winget nestabilní
            cmd = "winget list --accept-source-agreements"
            result = subprocess.run(cmd, capture_output=True, text=True, startupinfo=startupinfo, encoding='cp852', errors='replace')
            
            lines = result.stdout.splitlines()
            
            # Jednoduchý parser řádků
            # Přeskočíme hlavičku (obvykle první 2 řádky)
            start_index = 0
            for i, line in enumerate(lines):
                if line.startswith("Name") and "Id" in line and "Version" in line:
                    start_index = i + 2 # Header + Separator
                    break
            
            for line in lines[start_index:]:
                # Rozdělíme podle více mezer
                parts = re.split(r'\s{2,}', line.strip())
                
                if len(parts) >= 3:
                    name = parts[0]
                    app_id = parts[1]
                    version = parts[2]
                    available = ""
                    
                    # Pokud je k dispozici update, je ve 4. sloupci (index 3)
                    # Ale pozor, někdy je tam "Source", musíme zkontrolovat, jestli to vypadá jako verze
                    if len(parts) >= 4:
                        potential_available = parts[3]
                        # Jednoduchá heuristika: Verze začíná číslem
                        if potential_available and potential_available[0].isdigit():
                            available = potential_available
                    
                    app_data = {
                        "name": name,
                        "id": app_id,
                        "version": version,
                        "available": available
                    }
                    
                    installed_apps.append(app_data)
                    if available:
                        self.upgradable_apps.append(app_data)

            self.controller.after(0, self.display_apps, installed_apps)

        except Exception as e:
            print(f"Chyba při skenování: {e}")
            self.controller.after(0, self.scan_error)

    def scan_error(self):
        self.progress.stop()
        self.stats_label.config(text="Chyba při načítání aplikací.")
        self.refresh_btn.config(state="normal")

    def display_apps(self, apps):
        self.progress.stop()
        self.refresh_btn.config(state="normal")
        
        count_updatable = len(self.upgradable_apps)
        self.stats_label.config(text=f"Nainstalováno: {len(apps)} aplikací | Dostupné aktualizace: {count_updatable}")
        
        if count_updatable > 0:
            self.update_all_btn.config(state="normal", bg=COLORS['success'])
        else:
            self.update_all_btn.config(state="disabled", bg=COLORS['input_bg'])

        # Seřadíme: Nejdříve ty s updatem, pak abecedně
        apps.sort(key=lambda x: (0 if x['available'] else 1, x['name'].lower()))

        for app in apps:
            self.create_app_card(app)
            
        self.list_canvas.update_idletasks()
        self.list_scrollbar.redraw()

    def create_app_card(self, app):
        card = tk.Frame(self.list_scrollable, bg=COLORS['item_bg'], pady=10, padx=10)
        card.pack(fill='x', padx=(10,0), pady=5)

        # Icon
        icon_label = tk.Label(card, image=self.default_icon, bg=COLORS['item_bg'])
        icon_label.pack(side="left", padx=(0, 15))
        IconLoader.load_async(app, icon_label, self.controller)

        # Text Info
        text_frame = tk.Frame(card, bg=COLORS['item_bg'])
        text_frame.pack(side="left", fill="both", expand=True)
        
        tk.Label(text_frame, text=app['name'], font=("Segoe UI", 11, "bold"), bg=COLORS['item_bg'], fg="white", anchor="w").pack(fill="x")
        
        meta_text = f"ID: {app['id']} | Verze: {app['version']}"
        tk.Label(text_frame, text=meta_text, font=("Segoe UI", 9), bg=COLORS['item_bg'], fg=COLORS['sub_text'], anchor="w").pack(fill="x")

        # Status / Action area
        action_frame = tk.Frame(card, bg=COLORS['item_bg'])
        action_frame.pack(side="right")

        if app['available']:
            # Update Available
            tk.Label(action_frame, text=f"➔ {app['available']}", font=("Segoe UI", 9, "bold"), bg=COLORS['item_bg'], fg=COLORS['accent']).pack(side="left", padx=10)
            
            upd_btn = tk.Button(action_frame, text="Aktualizovat", font=("Segoe UI", 9, "bold"), 
                                bg=COLORS['success'], fg="white", relief="flat", padx=10, pady=2, cursor="hand2",
                                command=lambda: self.update_single(app))
            upd_btn.pack(side="right")
        else:
            # Up to date
            tk.Label(action_frame, text="✓ Aktuální", font=("Segoe UI", 9), bg=COLORS['item_bg'], fg="gray").pack(side="right", padx=10)

    def update_single(self, app):
        # Přidáme do fronty na instalaci (update je technicky reinstall novější verze)
        if "installer" in self.controller.views:
            installer = self.controller.views["installer"]
            # Upravíme data pro installer queue
            queue_item = {
                "name": app['name'],
                "id": app['id'],
                "version": app['available'], # Chceme nainstalovat novou verzi
                "website": "Unknown"
            }
            installer.add_item_to_queue(queue_item)
            messagebox.showinfo("Updater", f"{app['name']} byla přidána do instalační fronty.")
            # Volitelně přepnout: self.controller.switch_view("installer")

    def update_all(self):
        if not self.upgradable_apps: return
        
        if "installer" in self.controller.views:
            installer = self.controller.views["installer"]
            count = 0
            for app in self.upgradable_apps:
                queue_item = {
                    "name": app['name'],
                    "id": app['id'],
                    "version": app['available'],
                    "website": "Unknown"
                }
                installer.add_item_to_queue(queue_item)
                count += 1
            
            messagebox.showinfo("Updater", f"{count} aplikací bylo přidáno do instalační fronty.\nPřejděte na záložku Installer pro spuštění.")
            self.controller.switch_view("installer")

# --- OSTATNÍ STRÁNKY (AllAppsPage, InstallerPage, Placeholders) ---
# (Tyto třídy zůstávají stejné jako v předchozím kroku, zde je vložena AllAppsPage z minula pro úplnost)

class AllAppsPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=COLORS['bg_main'])
        self.controller = controller
        try: self.default_icon = ImageTk.PhotoImage(Image.new('RGB', (32, 32), color=COLORS['item_bg']))
        except: pass
        header_frame = tk.Frame(self, bg=COLORS['bg_main'], pady=15)
        header_frame.pack(fill='x')
        tk.Label(header_frame, text="Katalog aplikací", font=("Segoe UI", 18, "bold"), bg=COLORS['bg_main'], fg=COLORS['fg']).pack(side="left", padx=20)
        search_container = tk.Frame(self, bg=COLORS['bg_main'], padx=20)
        search_container.pack(fill='x')
        search_border = tk.Frame(search_container, bg=COLORS['input_bg'], bd=0) 
        search_border.pack(fill='x', ipady=2, pady=(0, 10))
        self.input_entry = tk.Entry(search_border, font=("Segoe UI", 12), bg=COLORS['input_bg'], fg="white", insertbackground="white", relief="flat")
        self.input_entry.pack(side='left', fill='both', expand=True, padx=10)
        self.input_entry.bind('<Return>', lambda event: self.start_search())
        self.search_btn = tk.Button(search_border, text="🔍", command=self.start_search, bg=COLORS['accent'], fg="white", relief="flat", padx=10, cursor="hand2")
        self.search_btn.pack(side='right', fill='y', padx=2, pady=2)
        filter_frame = tk.Frame(search_container, bg=COLORS['bg_main'])
        filter_frame.pack(fill='x', pady=(0, 15))
        tk.Label(filter_frame, text="Filtrovat:", font=("Segoe UI", 9, "bold"), bg=COLORS['bg_main'], fg=COLORS['sub_text']).pack(side="left", padx=(0, 10))
        self.create_filter_chip(filter_frame, "🌐 Internet", "Web Browsers")
        self.create_filter_chip(filter_frame, "🎵 Média", "Video Audio Player")
        self.create_filter_chip(filter_frame, "🛠️ Vývoj", "Development Tools")
        self.create_filter_chip(filter_frame, "🔧 Nástroje", "Utilities System")
        self.create_filter_chip(filter_frame, "🎮 Hry", "Gaming Launcher")
        self.progress = ttk.Progressbar(self, orient="horizontal", mode="indeterminate")
        self.results_container = tk.Frame(self, bg=COLORS['bg_sidebar'])
        self.results_container.pack(fill='both', expand=True, padx=20, pady=(0, 20))
        self.results_canvas = tk.Canvas(self.results_container, bg=COLORS['bg_sidebar'], highlightthickness=0)
        self.results_scrollbar = ModernScrollbar(self.results_container, command=self.results_canvas.yview, bg=COLORS['bg_sidebar'])
        self.results_scrollable = tk.Frame(self.results_canvas, bg=COLORS['bg_sidebar'])
        self.results_scrollable.bind("<Configure>", lambda e: self.results_canvas.configure(scrollregion=self.results_canvas.bbox("all")))
        self.results_canvas.create_window((0, 0), window=self.results_scrollable, anchor="nw", width=480)
        self.results_canvas.configure(yscrollcommand=self.results_scrollbar.set)
        self.results_canvas.bind("<Configure>", lambda e: self.results_canvas.itemconfig(self.results_canvas.find_all()[0], width=e.width))
        self.results_canvas.pack(side="left", fill="both", expand=True)
        self.results_scrollbar.pack(side="right", fill="y")
        self._bind_mousewheel(self.results_container, self.results_canvas)
        self.after(500, self.load_default_catalog)

    def load_default_catalog(self):
        self.progress.pack(fill='x', padx=20, pady=(0, 10))
        self.progress.start(10)
        threading.Thread(target=self.generate_default_apps_thread).start()

    def generate_default_apps_thread(self):
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = """Vygeneruj JSON seznam 30 nejpopulárnějších a nejpoužívanějších aplikací pro Windows, které jsou dostupné na Winget. Zahrň kategorie jako Prohlížeče, Média, Nástroje, Komunikace. VÝSTUPNÍ FORMÁT (čistý JSON pole): [{ "name": "Název aplikace", "id": "Přesné.Winget.ID", "version": "Latest", "website": "url_webu" }]"""
        try:
            response = model.generate_content(prompt)
            raw_text = response.text
            json_str = raw_text.replace("```json", "").replace("```", "").strip()
            match = re.search(r'\[.*\]', json_str, re.DOTALL)
            data = json.loads(match.group(0)) if match else []
            self.controller.after(0, self.display_results, data)
        except Exception as e:
            print(f"Chyba při načítání katalogu: {e}")
            self.controller.after(0, self.stop_loading)

    def create_filter_chip(self, parent, text, query):
        btn = tk.Button(parent, text=text, font=("Segoe UI", 9), bg=COLORS['item_bg'], fg=COLORS['fg'], relief="flat", padx=10, pady=2, cursor="hand2", command=lambda: self.run_category_search(query))
        btn.pack(side="left", padx=3)
        def on_enter(e): btn.config(bg=COLORS['item_hover'])
        def on_leave(e): btn.config(bg=COLORS['item_bg'])
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)

    def _bind_mousewheel(self, widget, canvas):
        def _on_mousewheel(event):
            if canvas.bbox("all"):
                scroll_height = canvas.bbox("all")[3]
                visible_height = canvas.winfo_height()
                if scroll_height <= visible_height: return 
            if event.num == 5 or event.delta < 0: canvas.yview_scroll(1, "units")
            elif event.num == 4 or event.delta > 0: canvas.yview_scroll(-1, "units")
            self.results_scrollbar.redraw()
        bind_enter = lambda e: {canvas.bind_all("<MouseWheel>", _on_mousewheel), canvas.bind_all("<Button-4>", _on_mousewheel), canvas.bind_all("<Button-5>", _on_mousewheel)}
        bind_leave = lambda e: {canvas.unbind_all("<MouseWheel>"), canvas.unbind_all("<Button-4>"), canvas.unbind_all("<Button-5>")}
        widget.bind('<Enter>', bind_enter)
        widget.bind('<Leave>', bind_leave)

    def start_search(self):
        query = self.input_entry.get()
        if not query: return
        self.run_category_search(query)

    def run_category_search(self, query):
        self.progress.pack(fill='x', padx=20, pady=(0, 10))
        self.progress.start(10)
        for widget in self.results_scrollable.winfo_children(): widget.destroy()
        threading.Thread(target=self.search_thread, args=(query,)).start()

    def search_thread(self, query):
        try:
            cmd = f'winget search "{query}" --source winget --accept-source-agreements -n 15'
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            result = subprocess.run(cmd, capture_output=True, text=True, startupinfo=startupinfo, encoding='cp852', errors='replace')
            model = genai.GenerativeModel('gemini-2.5-flash')
            prompt = f"""Parsuj tento výstup z winget search na JSON. Ignoruj balast a ID začínající na "msstore". VÝSTUP: '''{result.stdout}''' JSON FORMAT: [{{ "name": "...", "id": "...", "version": "...", "website": "..." }}]"""
            response = model.generate_content(prompt)
            json_str = response.text.replace("```json", "").replace("```", "").strip()
            match = re.search(r'\[.*\]', json_str, re.DOTALL)
            data = json.loads(match.group(0)) if match else []
            for item in data:
                 if not item.get('version') or item['version'] == "Latest": item['version'] = "Latest/Unknown"
            self.controller.after(0, self.display_results, data)
        except Exception as e:
            print(e)
            self.controller.after(0, self.stop_loading)

    def stop_loading(self):
        self.progress.stop()
        self.progress.pack_forget()

    def display_results(self, items):
        self.stop_loading()
        for widget in self.results_scrollable.winfo_children(): widget.destroy()
        if not items:
            tk.Label(self.results_scrollable, text="Nic nenalezeno.", bg=COLORS['bg_sidebar'], fg="gray").pack(pady=20)
            return
        for item in items: self.create_item(item)
        self.results_canvas.update_idletasks()
        self.results_scrollbar.redraw()

    def create_item(self, item_data):
        card = tk.Frame(self.results_scrollable, bg=COLORS['item_bg'], pady=10, padx=10)
        card.pack(fill='x', padx=(10,0), pady=5)
        icon_label = tk.Label(card, image=self.default_icon, bg=COLORS['item_bg'])
        icon_label.pack(side="left", padx=(0, 15))
        IconLoader.load_async(item_data, icon_label, self.controller)
        text_frame = tk.Frame(card, bg=COLORS['item_bg'])
        text_frame.pack(side="left", fill="both", expand=True)
        tk.Label(text_frame, text=item_data.get("name"), font=("Segoe UI", 11, "bold"), bg=COLORS['item_bg'], fg="white", anchor="w").pack(fill="x")
        tk.Label(text_frame, text=f"ID: {item_data.get('id')}", font=("Segoe UI", 9), bg=COLORS['item_bg'], fg=COLORS['sub_text'], anchor="w").pack(fill="x")
        action_symbol = tk.Label(card, text="＋", font=("Arial", 18), bg=COLORS['item_bg'], fg=COLORS['accent'], cursor="hand2", padx=10)
        action_symbol.pack(side="right")
        action_symbol.bind("<Button-1>", lambda e, i=item_data: self.add_to_main_queue(i))
        def on_enter_sym(e): action_symbol.config(bg=COLORS['accent'], fg="white")
        def on_leave_sym(e): action_symbol.config(bg=COLORS['item_bg'], fg=COLORS['accent'])
        action_symbol.bind("<Enter>", on_enter_sym)
        action_symbol.bind("<Leave>", on_leave_sym)
        widgets = [card, text_frame, icon_label] + text_frame.winfo_children()
        def on_enter_card(e):
            for w in widgets: w.config(bg=COLORS['item_hover'])
            if e.widget != action_symbol: action_symbol.config(bg=COLORS['item_hover'])
        def on_leave_card(e):
            for w in widgets: w.config(bg=COLORS['item_bg'])
            if e.widget != action_symbol: action_symbol.config(bg=COLORS['item_bg'])
        card.bind("<Enter>", on_enter_card)
        card.bind("<Leave>", on_leave_card)

    def add_to_main_queue(self, item):
        if "installer" in self.controller.views:
            installer_page = self.controller.views["installer"]
            installer_page.add_item_to_queue(item)
            messagebox.showinfo("Přidáno", f"{item['name']} byla přidána do fronty.")
        else: messagebox.showerror("Chyba", "Instalační stránka není dostupná.")

class InstallerPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=COLORS['bg_main'])
        self.controller = controller
        try: self.default_icon = ImageTk.PhotoImage(Image.new('RGB', (32, 32), color=COLORS['item_bg']))
        except: pass
        self.queue_data = {} 
        self.is_searching = False
        self.columnconfigure(0, weight=1, uniform="group1") 
        self.columnconfigure(1, weight=1, uniform="group1") 
        self.rowconfigure(0, weight=0) 
        self.rowconfigure(1, weight=0) 
        self.rowconfigure(2, weight=1) 
        header_frame = tk.Frame(self, bg=COLORS['bg_main'], pady=15)
        header_frame.grid(row=0, column=0, columnspan=2, sticky="ew")
        tk.Label(header_frame, text="Installer", font=("Segoe UI", 18, "bold"), bg=COLORS['bg_main'], fg=COLORS['fg']).pack(side="left", padx=20)
        left_controls = tk.Frame(self, bg=COLORS['bg_main'], padx=20)
        left_controls.grid(row=1, column=0, sticky="nsew")
        tk.Label(left_controls, text="Zadejte název programu", font=("Segoe UI", 14, "bold"), bg=COLORS['bg_main'], fg=COLORS['fg'], anchor="w").pack(fill='x')
        tk.Label(left_controls, text="(Nebo popište, co hledáte, např. 'úprava zvuku')", font=("Segoe UI", 9), bg=COLORS['bg_main'], fg=COLORS['sub_text'], anchor="w").pack(fill='x', pady=(0, 10))
        search_frame = tk.Frame(left_controls, bg=COLORS['bg_main'])
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
        tk.Label(left_controls, text="Výsledky hledání:", font=("Segoe UI", 11, "bold"), bg=COLORS['bg_main'], fg=COLORS['sub_text'], anchor="w").pack(fill='x', pady=(10, 5), side="bottom")
        right_controls = tk.Frame(self, bg=COLORS['bg_main'], padx=20)
        right_controls.grid(row=1, column=1, sticky="sew") 
        queue_header_row = tk.Frame(right_controls, bg=COLORS['bg_main'])
        queue_header_row.pack(fill='x', pady=(10, 5), side="bottom")
        tk.Label(queue_header_row, text="Instalační fronta:", font=("Segoe UI", 11, "bold"), bg=COLORS['bg_main'], fg=COLORS['sub_text']).pack(side="left")
        actions_frame = tk.Frame(queue_header_row, bg=COLORS['bg_main'])
        actions_frame.pack(side="right")
        self.create_header_btn(actions_frame, "📂", self.import_queue, "Importovat seznam", COLORS['input_bg'], COLORS['item_hover'])
        self.create_header_btn(actions_frame, "🗑️", self.clear_queue, "Vymazat frontu", COLORS['danger'], COLORS['danger_hover'])
        self.create_header_btn(actions_frame, "💾", self.save_only, "Uložit .bat soubor", COLORS['input_bg'], COLORS['item_hover'])
        self.create_header_btn(actions_frame, "🚀", self.install_now, "Instalovat vše", COLORS['success'], COLORS['success_hover'])
        left_list_frame = tk.Frame(self, bg=COLORS['bg_main'], padx=20)
        left_list_frame.grid(row=2, column=0, sticky="nsew")
        self.found_container = tk.Frame(left_list_frame, bg=COLORS['bg_sidebar'])
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
        right_list_frame = tk.Frame(self, bg=COLORS['bg_main'], padx=20)
        right_list_frame.grid(row=2, column=1, sticky="nsew")
        self.queue_container = tk.Frame(right_list_frame, bg=COLORS['bg_sidebar'])
        self.queue_container.pack(fill='both', expand=True, pady=(0, 20))
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

    def create_header_btn(self, parent, text, command, tooltip_text, bg_color, hover_color):
        btn = tk.Button(parent, text=text, command=command, bg=bg_color, fg="white", font=("Segoe UI Emoji", 12), relief="flat", width=3, cursor="hand2", borderwidth=0)
        btn.pack(side="left", padx=2)
        def on_enter(e):
            if btn['state'] != 'disabled': btn.config(bg=hover_color)
        def on_leave(e):
            if btn['state'] != 'disabled': btn.config(bg=bg_color)
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        ToolTip(btn, tooltip_text)
        return btn

    def import_queue(self):
        file_path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt"), ("Batch files", "*.bat"), ("All files", "*.*")])
        if file_path:
             messagebox.showinfo("Import", f"Vybrán soubor: {file_path}\n(Funkce importu zatím není plně implementována)")

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
        intent_prompt = f"""
        Jsi expert na Windows software a Winget repozitář.
        Uživatel zadal: "{user_request}"
        Tvým úkolem je rozhodnout, jak tento dotaz hledat ve Winget.
        SCÉNÁŘ A (Konkrétní aplikace): Pokud uživatel myslí konkrétní program (i s překlepem), vráť POUZE opravený název.
        SCÉNÁŘ B (Obecný popis/Kategorie): Pokud uživatel hledá typ programu, vyber několik NEJLEPŠÍCH aplikací.
        Odpověz POUZE v tomto formátu: QUERIES: název1;název2;název3
        """
        search_terms = []
        try:
            intent_response = model.generate_content(intent_prompt)
            raw_intent = intent_response.text.strip()
            if "QUERIES:" in raw_intent:
                clean_line = raw_intent.replace("QUERIES:", "").strip()
                search_terms = [t.strip() for t in clean_line.split(";") if t.strip()]
            else:
                search_terms = [user_request]
            print(f"AI navrhlo hledat tyto výrazy: {search_terms}")
        except Exception as e:
            print(f"Chyba při zjišťování záměru: {e}")
            search_terms = [user_request]

        combined_output = ""
        self.progress['maximum'] = len(search_terms) * 100
        current_prog = 0
        
        for term in search_terms:
            try:
                cmd = f'winget search "{term}" --source winget --accept-source-agreements -n 3'
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                print(f"Spouštím Winget pro: {term}")
                result = subprocess.run(cmd, capture_output=True, text=True, startupinfo=startupinfo, encoding='cp852', errors='replace')
                combined_output += f"\n--- VÝSLEDKY PRO '{term}' ---\n"
                combined_output += result.stdout
            except Exception as e:
                print(f"Winget search selhal pro {term}: {e}")
            current_prog += 100

        filter_prompt = f"""
        Mám výstup z příkazové řádky (Winget Search). Původní dotaz: "{user_request}"
        SUROVÁ DATA: '''{combined_output}'''
        INSTRUKCE: Analyzuj data, ignoruj balast, extrahuj Název, ID, Verzi.
        VÝSTUP (JSON pole): [{{ "name": "...", "id": "...", "version": "...", "website": "..." }}]
        """
        try:
            response = model.generate_content(filter_prompt)
            raw_text = response.text
            json_str = raw_text.replace("```json", "").replace("```", "").strip()
            json_match = re.search(r'\[.*\]', json_str, re.DOTALL)
            data = json.loads(json_match.group(0)) if json_match else []
            for item in data:
                if not item.get('version') or item['version'] == "Latest": item['version'] = "Latest/Unknown"
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
        for item in items: self.create_list_item(self.found_scrollable, item, is_result_mode=True)
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

class PlaceholderPage(tk.Frame):
    def __init__(self, parent, title, icon_emoji="✨"):
        super().__init__(parent, bg=COLORS['bg_main'])
        center_frame = tk.Frame(self, bg=COLORS['bg_main'])
        center_frame.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(center_frame, text=icon_emoji, font=("Segoe UI Emoji", 48), bg=COLORS['bg_main']).pack(pady=(0, 20))
        tk.Label(center_frame, text=f"Vítejte v {title}", font=("Segoe UI", 18, "bold"), bg=COLORS['bg_main'], fg="white").pack()
        tk.Label(center_frame, text="Vyberte akci z menu vlevo", font=("Segoe UI", 10), bg=COLORS['bg_main'], fg=COLORS['sub_text']).pack(pady=(5, 20))

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

        # VYNUCENÍ BARVY LIŠTY
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
        self.views["all_apps"] = AllAppsPage(self.content_area, self)
        self.views["updater"] = UpdaterPage(self.content_area, self) # ZDE JE ZMĚNA
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