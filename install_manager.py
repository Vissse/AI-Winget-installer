# install_manager.py
import tkinter as tk
from tkinter import scrolledtext, ttk
import threading
import subprocess
import queue
import os
import shutil
from config import COLORS

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