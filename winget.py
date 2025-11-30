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
import random # Přidáno pro náhodné hlášky při načítání

# --- KONFIGURACE ---
API_KEY = "AIzaSyC04q0Magnd7hV6oC-mh6zvd4UUT6kxhsY" 
OUTPUT_FILE = "install_apps.bat"

# --- BAREVNÉ SCHÉMA (MODERN DASHBOARD) ---
COLORS = {
    "bg": "#1e1e1e",          # Tmavší pozadí pro celé okno
    "panel_bg": "#252526",    # Pozadí panelů
    "fg": "#ffffff",
    "accent": "#007acc",      # VS Code modrá
    "accent_hover": "#0098ff",
    "success": "#3fb950",     # GitHub zelená
    "success_hover": "#56d364",
    "danger": "#f85149",      # Červená
    "danger_hover": "#ff7b72",
    "item_bg": "#2d2d2d",     # Karty
    "item_hover": "#383838",
    "input_bg": "#3c3c3c",
    "scrollbar_bg": "#252526",
    "scrollbar_thumb": "#424242",
    "scrollbar_hover": "#4f4f4f",
    "sub_text": "#8b949e",
    "border": "#30363d"
}

genai.configure(api_key=API_KEY)

# --- KOMPONENTY ---

class ModernScrollbar(tk.Canvas):
    def __init__(self, parent, command=None, width=10, bg=COLORS['panel_bg'], thumb_color=COLORS['scrollbar_thumb']):
        super().__init__(parent, width=width, bg=bg, highlightthickness=0)
        self.command = command
        self.thumb_color = thumb_color
        self.hover_color = COLORS['scrollbar_hover']
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

def get_real_version(app_id):
    try:
        cmd = f'winget search --id {app_id} --exact --source winget --accept-source-agreements'
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        result = subprocess.run(cmd, capture_output=True, text=True, startupinfo=startupinfo, encoding='cp852', errors='replace')
        lines = result.stdout.splitlines()
        for line in lines:
            parts = line.split()
            if len(parts) >= 3 and app_id.lower() in [p.lower() for p in parts]:
                for i, part in enumerate(parts):
                    if part.lower() == app_id.lower() and i + 1 < len(parts):
                        return parts[i+1]
        return None
    except Exception:
        return None

# --- SPLASH SCREEN (ANIMOVANÝ START) ---
class SplashScreen(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Načítání...")
        
        # Nastavení velikosti a pozice
        w = 450
        h = 280
        ws = self.winfo_screenwidth()
        hs = self.winfo_screenheight()
        x = (ws/2) - (w/2)
        y = (hs/2) - (h/2)
        
        self.geometry('%dx%d+%d+%d' % (w, h, x, y))
        self.overrideredirect(True) # Odstraní rámeček okna (minimalizace, zavřít atd.)
        self.configure(bg=COLORS['bg'])
        
        # Hlavní kontejner s ohraničením
        main_frame = tk.Frame(self, bg=COLORS['bg'], highlightbackground=COLORS['accent'], highlightthickness=2)
        main_frame.pack(fill='both', expand=True)

        # Logo / Nadpis
        tk.Label(main_frame, text="AI Winget Installer", font=("Segoe UI", 22, "bold"), bg=COLORS['bg'], fg=COLORS['fg']).pack(pady=(50, 5))
        tk.Label(main_frame, text="Alpha verze 1.0", font=("Segoe UI", 10), bg=COLORS['bg'], fg=COLORS['accent']).pack(pady=(0, 40))

        # Loading text
        self.loading_label = tk.Label(main_frame, text="Inicializace...", font=("Segoe UI", 9), bg=COLORS['bg'], fg=COLORS['sub_text'])
        self.loading_label.pack(pady=(0, 5))

        # Progress bar
        style = ttk.Style()
        style.theme_use('default')
        style.configure("Splash.Horizontal.TProgressbar", background=COLORS['accent'], troughcolor=COLORS['panel_bg'], borderwidth=0, thickness=6)
        
        self.progress = ttk.Progressbar(main_frame, orient="horizontal", length=350, mode="determinate", style="Splash.Horizontal.TProgressbar")
        self.progress.pack()

        # Spuštění animace
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
            # Zvýšení progressu
            increment = random.randint(1, 4)
            self.progress_val += increment
            self.progress['value'] = self.progress_val
            
            # Změna textu v průběhu
            if self.progress_val > 20 and self.step_index == 0:
                self.step_index = 1
                self.loading_label.config(text=self.loading_steps[1])
            elif self.progress_val > 50 and self.step_index == 1:
                self.step_index = 2
                self.loading_label.config(text=self.loading_steps[2])
            elif self.progress_val > 80 and self.step_index == 2:
                self.step_index = 3
                self.loading_label.config(text=self.loading_steps[3])
            
            # Rychlost animace (čím menší číslo, tím rychlejší)
            self.after(30, self.animate)
        else:
            self.loading_label.config(text=self.loading_steps[4])
            self.after(500, self.close_splash)

    def close_splash(self):
        self.destroy()
        self.master.deiconify() # Zobrazí hlavní okno


# --- OKNO INSTALACE ---
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
        self.top.configure(bg=COLORS['bg'])
        
        self.install_list = install_list
        self.total_apps = len(install_list)
        self.current_app_index = 0
        self.failed_apps = []
        self.is_running = True

        self.title_label = tk.Label(self.top, text="🚀 Příprava instalace...", font=("Segoe UI", 16, "bold"), bg=COLORS['bg'], fg="white")
        self.title_label.pack(pady=(20, 10))

        style = ttk.Style()
        style.theme_use('default')
        style.configure("Green.Horizontal.TProgressbar", background=COLORS['success'], troughcolor=COLORS['input_bg'], borderwidth=0, thickness=20)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.top, variable=self.progress_var, maximum=self.total_apps, style="Green.Horizontal.TProgressbar")
        self.progress_bar.pack(fill='x', padx=30, pady=10)

        info_frame = tk.Frame(self.top, bg=COLORS['bg'])
        info_frame.pack(fill='x', padx=30)
        self.status_label = tk.Label(info_frame, text=f"Inicializace...", font=("Segoe UI", 11), bg=COLORS['bg'], fg=COLORS['sub_text'])
        self.status_label.pack(side='left')

        tk.Label(self.top, text="Detailní výpis:", font=("Segoe UI", 10, "bold"), bg=COLORS['bg'], fg="#555").pack(pady=(20, 5), anchor="w", padx=30)
        self.text_area = scrolledtext.ScrolledText(self.top, font=("Consolas", 9), bg="#111", fg="#cccccc", insertbackground="white", relief="flat", height=15, highlightthickness=1, highlightbackground=COLORS['border'])
        self.text_area.pack(fill='both', expand=True, padx=30, pady=(0, 10))

        self.close_btn = tk.Button(self.top, text="Zrušit", command=self.close_window, bg=COLORS['danger'], fg="white", font=("Segoe UI", 10), relief="flat", padx=25, pady=8, cursor="hand2")
        self.close_btn.pack(pady=15)
        self.close_btn.bind("<Enter>", lambda e: self.on_hover(self.close_btn, COLORS['danger_hover']))
        self.close_btn.bind("<Leave>", lambda e: self.on_leave(self.close_btn, COLORS['danger']))

        self.msg_queue = queue.Queue()
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
            failed_str = ", ".join(self.failed_apps)
            self.status_label.config(text=f"Nepodařilo se nainstalovat: {failed_str}", fg=COLORS['danger'])


# --- HLAVNÍ APLIKACE (NOVÝ DESIGN NA ŠÍŘKU) ---
class WingetApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Winget Installer")
        
        # Nastavení okna na šířku
        w = 1100
        h = 700
        ws = root.winfo_screenwidth()
        hs = root.winfo_screenheight()
        x = (ws/2) - (w/2)
        y = (hs/2) - (h/2)
        self.root.geometry('%dx%d+%d+%d' % (w, h, x, y))
        self.root.configure(bg=COLORS['bg'])
        
        try:
            app_icon = tk.PhotoImage(file="program_icon.png")
            self.root.iconphoto(True, app_icon)
        except: pass
        self.default_icon = ImageTk.PhotoImage(Image.new('RGB', (32, 32), color=COLORS['item_bg']))

        self.queue_data = {} 
        self.is_searching = False

        # --- HLAVNÍ ROZLOŽENÍ (GRID) ---
        self.root.columnconfigure(0, weight=1, uniform="group1") # Levý sloupec
        self.root.columnconfigure(1, weight=1, uniform="group1") # Pravý sloupec
        self.root.rowconfigure(0, weight=0) # Nadpis
        self.root.rowconfigure(1, weight=1) # Obsah

        # --- 1. HEADER (Společný) ---
        header_frame = tk.Frame(self.root, bg=COLORS['bg'], pady=15)
        header_frame.grid(row=0, column=0, columnspan=2, sticky="ew")
        
        # Nadpis vlevo
        tk.Label(header_frame, text="AI Winget Installer", font=("Segoe UI", 18, "bold"), bg=COLORS['bg'], fg=COLORS['fg']).pack(side="left", padx=20)

        # --- UPDATE: VIZITKA ALPHA VERZE ---
        # Umístění vizitky v hlavičce (vhodné místo)
        tk.Label(header_frame, text="Alpha verze 1.0", font=("Segoe UI", 10), bg=COLORS['bg'], fg=COLORS['sub_text']).pack(side="right", padx=20)

        # --- LEVÝ PANEL (VYHLEDÁVÁNÍ) ---
        left_panel = tk.Frame(self.root, bg=COLORS['bg'], padx=20, pady=10)
        left_panel.grid(row=1, column=0, sticky="nsew")
        
        # Nápis + Subtext
        tk.Label(left_panel, text="Zadejte název programu", font=("Segoe UI", 14, "bold"), bg=COLORS['bg'], fg=COLORS['fg'], anchor="w").pack(fill='x')
        tk.Label(left_panel, text="(Nebo popište, co hledáte, např. 'úprava zvuku')", font=("Segoe UI", 9), bg=COLORS['bg'], fg=COLORS['sub_text'], anchor="w").pack(fill='x', pady=(0, 10))
        
        # Search Box
        search_frame = tk.Frame(left_panel, bg=COLORS['bg'])
        search_frame.pack(fill='x', pady=(0, 10))
        
        # --- UPDATE: ODSTRANĚNÍ BORDERU ---
        # bd=0 a highlightthickness=0 odstraní černý rámeček
        search_border = tk.Frame(search_frame, bg=COLORS['input_bg'], bd=0, highlightthickness=0) 
        search_border.pack(fill='x', ipady=2)
        
        self.input_entry = tk.Entry(search_border, font=("Segoe UI", 12), bg=COLORS['input_bg'], fg="white", insertbackground="white", relief="flat")
        self.input_entry.pack(side='left', fill='both', expand=True, padx=10)
        self.input_entry.bind('<Return>', lambda event: self.start_search())

        self.search_btn = self.create_animated_btn(search_border, "Hledat", self.start_search, COLORS['accent'], COLORS['accent_hover'])
        self.search_btn.pack(side='right', fill='y', padx=2, pady=2)

        style = ttk.Style()
        style.theme_use('default')
        style.configure("Horizontal.TProgressbar", background=COLORS['accent'], troughcolor=COLORS['bg'], borderwidth=0, thickness=2)
        self.progress = ttk.Progressbar(search_frame, orient="horizontal", mode="indeterminate", style="Horizontal.TProgressbar")

        # Seznam výsledků
        tk.Label(left_panel, text="Výsledky hledání:", font=("Segoe UI", 11, "bold"), bg=COLORS['bg'], fg=COLORS['sub_text'], anchor="w").pack(fill='x', pady=(10, 5))
        
        self.found_container = tk.Frame(left_panel, bg=COLORS['panel_bg'])
        
        # --- UPDATE: ZAROVNÁNÍ ---
        # pady=(0, 20) zajistí, že seznam končí 20px od spodku panelu.
        # To přesně odpovídá pravému panelu, kde 'footer' má pady=20 (takže tlačítka končí 20px od spodku).
        self.found_container.pack(fill='both', expand=True, pady=(0, 20))
        
        self.found_canvas = tk.Canvas(self.found_container, bg=COLORS['panel_bg'], highlightthickness=0)
        self.found_scrollbar = ModernScrollbar(self.found_container, command=self.found_canvas.yview, bg=COLORS['panel_bg'])
        self.found_scrollable = tk.Frame(self.found_canvas, bg=COLORS['panel_bg'])
        
        self.found_scrollable.bind("<Configure>", self.on_frame_configure)
        self.found_canvas.create_window((0, 0), window=self.found_scrollable, anchor="nw", width=480)
        self.found_canvas.configure(yscrollcommand=self.found_scrollbar.set)
        self.found_canvas.bind("<Configure>", lambda e: self.found_canvas.itemconfig(self.found_canvas.find_all()[0], width=e.width))

        self.found_canvas.pack(side="left", fill="both", expand=True)
        self.found_scrollbar.pack(side="right", fill="y")
        self._bind_mousewheel(self.found_container, self.found_canvas)


        # --- PRAVÝ PANEL (FRONTA) ---
        right_panel = tk.Frame(self.root, bg=COLORS['bg'], padx=20, pady=10)
        right_panel.grid(row=1, column=1, sticky="nsew")

        # Nadpis
        queue_header = tk.Frame(right_panel, bg=COLORS['bg'])
        queue_header.pack(fill='x', pady=(0, 10))
        tk.Label(queue_header, text="Instalační fronta:", font=("Segoe UI", 11, "bold"), bg=COLORS['bg'], fg=COLORS['sub_text']).pack(side="left")

        # --- FOOTER (TLAČÍTKA) ---
        # Používáme side="bottom", aby footer vždy seděl dole a seznam nad ním se roztahoval
        right_footer = tk.Frame(right_panel, bg=COLORS['bg'], pady=20)
        right_footer.pack(side="bottom", fill='x')

        self.create_animated_btn(right_footer, "Vymazat frontu", self.clear_queue, COLORS['danger'], COLORS['danger_hover']).pack(side="left")
        self.create_animated_btn(right_footer, "Uložit instalační soubor", self.save_only, COLORS['accent'], COLORS['accent_hover']).pack(side="left", padx=10)
        self.create_animated_btn(right_footer, "INSTALOVAT VŠE", self.install_now, COLORS['success'], COLORS['success_hover']).pack(side="right", fill='x', expand=True, padx=(10, 0))

        # Seznam fronty (zbytek místa mezi hlavičkou a patičkou)
        self.queue_container = tk.Frame(right_panel, bg=COLORS['panel_bg'])
        self.queue_container.pack(fill='both', expand=True)

        self.queue_canvas = tk.Canvas(self.queue_container, bg=COLORS['panel_bg'], highlightthickness=0)
        self.queue_scrollbar = ModernScrollbar(self.queue_container, command=self.queue_canvas.yview, bg=COLORS['panel_bg'])
        self.queue_scrollable = tk.Frame(self.queue_canvas, bg=COLORS['panel_bg'])
        
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
            # Kontrola, zda je co scrollovat (bbox vs height)
            if canvas.bbox("all"):
                scroll_height = canvas.bbox("all")[3]
                visible_height = canvas.winfo_height()
                if scroll_height <= visible_height: return # Nescrollovat, pokud se vše vejde
            
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
        
        # 1. KROK: Live search
        print(f"Spouštím live winget search pro: {user_request}")
        raw_winget_output = ""
        try:
            # Přidáme --source winget, abychom hledali jen v ofiko repozitáři
            # Odstraníme omezení počtu výsledků, aby se tam vešlo všechno
            cmd = f'winget search "{user_request}" --source winget --accept-source-agreements'
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            result = subprocess.run(cmd, capture_output=True, text=True, startupinfo=startupinfo, encoding='cp852', errors='replace')
            raw_winget_output = result.stdout
        except Exception as e:
            print(f"Winget search selhal: {e}")

        # 2. KROK: AI Filtr (Upravený)
        prompt = f"""
        Jsi inteligentní asistent pro instalaci software na Windows.
        
        UŽIVATEL HLEDÁ: "{user_request}"
        
        VÝSTUP Z WINGET SEARCH:
        '''
        {raw_winget_output}
        '''

        INSTRUKCE:
        1. Tvým úkolem je najít v datech aplikaci, kterou uživatel hledá.
        2. Pokud hledá konkrétní název (např. "Zen Browser", "Brave"), najdi záznam, který tomu nejlépe odpovídá. 
           - TIP: Pro "Zen Browser" hledej ID obsahující "Zen-Team" nebo "Zen-Browser".
           - TIP: Pro "Brave" je to ID "Brave.Brave".
        3. Pokud nic nenajdeš v datech, ale víš, že aplikace existuje a znáš její pravděpodobné ID, použij svou znalost (např. Zen Browser je novinka, ID bývá 'Zen-Team.Zen-Browser').
        4. Ignoruj balast (knihovny, drivery), pokud to není to, co uživatel explicitně chce.
        
        VÝSTUPNÍ FORMÁT (JSON):
        [
            {{ 
                "name": "Název aplikace", 
                "id": "Přesné.ID", 
                "version": "verze (nebo 'Latest')", 
                "website": "odhadni-domenu.com (např. zen-browser.app)" 
            }}
        ]
        """

        try:
            response = model.generate_content(prompt)
            raw_text = response.text
            json_match = re.search(r'\[.*\]', raw_text, re.DOTALL)
            
            data = []
            if json_match:
                data = json.loads(json_match.group(0))
            else:
                data = json.loads(raw_text.replace("```json", "").replace("```", "").strip())
            
            # Pokud verze chybí, pokusíme se ji zjistit, ale pro Zen Browser to může selhat, tak necháme co tam je
            for item in data:
                real_version = get_real_version(item['id'])
                if real_version: 
                    item['version'] = real_version
                elif not item.get('version') or item['version'] == "Unknown":
                    item['version'] = "Latest"

            self.root.after(0, self.display_search_results, data)

        except Exception as e:
            print(f"Chyba: {e}")
            self.root.after(0, lambda: messagebox.showerror("Chyba AI", f"Chyba zpracování.\nDetail: {e}"))
            self.root.after(0, self.stop_loading_animation)

    def stop_loading_animation(self):
        self.progress.stop()
        self.progress.pack_forget()
        self.is_searching = False
        self.search_btn.config(cursor="hand2")

    def display_search_results(self, items):
        self.stop_loading_animation()
        for widget in self.found_scrollable.winfo_children(): widget.destroy()
        if not items:
            tk.Label(self.found_scrollable, text="Nic nenalezeno.", bg=COLORS['panel_bg'], fg="gray").pack(pady=20)
            return
        for item in items:
            self.create_list_item(self.found_scrollable, item, is_result_mode=True)
        self.found_canvas.update_idletasks()
        self.found_scrollbar.redraw()

    def create_list_item(self, parent_scrollable, item_data, is_result_mode):
        name = item_data.get("name")
        app_id = item_data.get("id")
        version = item_data.get("version")
        
        # Karta
        card = tk.Frame(parent_scrollable, bg=COLORS['item_bg'], pady=10, padx=10)
        card.pack(fill='x', padx=(10,0), pady=5)

        # Ikona
        icon_label = tk.Label(card, image=self.default_icon, bg=COLORS['item_bg'])
        icon_label.pack(side="left", padx=(0, 15))
        IconLoader.load_async(item_data, icon_label, self.root)

        # Text
        text_frame = tk.Frame(card, bg=COLORS['item_bg'])
        text_frame.pack(side="left", fill="both", expand=True)
        tk.Label(text_frame, text=name, font=("Segoe UI", 11, "bold"), bg=COLORS['item_bg'], fg="white", anchor="w").pack(fill="x")
        tk.Label(text_frame, text=f"ID: {app_id} | v{version}", font=("Segoe UI", 9), bg=COLORS['item_bg'], fg=COLORS['sub_text'], anchor="w").pack(fill="x")

        # Akce
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
            messagebox.showerror("Chyba", str(e)); return False

    def save_only(self):
        if self._create_batch_file(): messagebox.showinfo("Uloženo", f"Soubor: {OUTPUT_FILE}")

    def install_now(self):
        if self._create_batch_file(): InstallationDialog(self.root, list(self.queue_data.values()))

if __name__ == "__main__":
    root = tk.Tk()
    
    # --- UPDATE: Skrytí hlavního okna při startu ---
    root.withdraw()
    
    app = WingetApp(root)
    
    # --- UPDATE: Zobrazení Splash Screenu ---
    splash = SplashScreen(root)
    
    root.mainloop()