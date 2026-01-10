# updater.py
import requests
import os
import sys
import subprocess
import tkinter as tk
from tkinter import messagebox, ttk
from packaging import version
import threading
import tempfile # Potřeba pro práci s Temp složkou
from pathlib import Path
from config import CURRENT_VERSION 

GITHUB_USER = "Vissse"
REPO_NAME = "Winget-Installer"

class UpdateProgressDialog(tk.Toplevel):
    def __init__(self, parent, total_size, download_url, on_success, on_fail):
        super().__init__(parent)
        self.title("Aktualizace aplikace")
        self.geometry("400x150")
        self.resizable(False, False)
        try:
            ws, hs = self.winfo_screenwidth(), self.winfo_screenheight()
            x, y = (ws/2) - (200), (hs/2) - (75)
            self.geometry(f"400x150+{int(x)}+{int(y)}")
        except: pass
        self.configure(bg="#1e1e1e")
        self.grab_set()
        
        self.lbl_info = tk.Label(self, text="Stahuji aktualizaci...", font=("Segoe UI", 12, "bold"), bg="#1e1e1e", fg="white")
        self.lbl_info.pack(pady=(20, 10))
        
        self.progress_var = tk.DoubleVar()
        self.progress = ttk.Progressbar(self, variable=self.progress_var, maximum=100)
        self.progress.pack(fill="x", padx=40, pady=10)
        
        self.status_lbl = tk.Label(self, text="0%", font=("Segoe UI", 10), bg="#1e1e1e", fg="#aaaaaa")
        self.status_lbl.pack()
        
        self.download_url = download_url
        self.total_size = total_size
        self.on_success = on_success
        self.on_fail = on_fail
        self.is_downloading = True
        
        # ZDE JE ZMĚNA: Stahujeme do dočasné složky
        self.temp_dir = tempfile.gettempdir()
        self.target_temp_file = os.path.join(self.temp_dir, f"WingetInstaller_Update_{random.randint(1000,9999)}.exe")
        
        threading.Thread(target=self.download_thread, daemon=True).start()

    def download_thread(self):
        try:
            # Úklid předchozích pokusů
            if os.path.exists(self.target_temp_file):
                try: os.remove(self.target_temp_file)
                except: pass
            
            response = requests.get(self.download_url, stream=True)
            downloaded = 0
            with open(self.target_temp_file, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if not self.is_downloading: break
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if self.total_size > 0:
                            percent = (downloaded / self.total_size) * 100
                            self.after(0, lambda p=percent: self.update_ui(p))
            
            if self.total_size > 0 and downloaded < self.total_size: 
                raise Exception("Stažený soubor je nekompletní.")
                
            # Předáme cestu ke staženému souboru dál
            self.after(0, lambda: self.on_success(self.target_temp_file))
            self.after(0, self.destroy)
            
        except Exception as e:
            if os.path.exists(self.target_temp_file): 
                try: os.remove(self.target_temp_file)
                except: pass
            self.after(0, lambda: messagebox.showerror("Chyba", f"Stahování selhalo:\n{e}"))
            self.after(0, self.on_fail)
            self.after(0, self.destroy)

    def update_ui(self, percent):
        self.progress_var.set(percent)
        self.status_lbl.config(text=f"{int(percent)} %")

class GitHubUpdater:
    def __init__(self, parent_window=None):
        self.parent = parent_window
        self.api_url = f"https://api.github.com/repos/{GITHUB_USER}/{REPO_NAME}/releases/latest"

    def check_for_updates(self, silent=False, on_continue=None):
        try:
            response = requests.get(self.api_url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                latest_tag = data.get("tag_name", "0.0.0").lstrip("v")
                if version.parse(latest_tag) > version.parse(CURRENT_VERSION):
                    asset_url, size = self._get_exe_info(data)
                    if asset_url:
                        self.parent.after(0, lambda: self._prompt_update(latest_tag, asset_url, size, on_continue))
                        return
                    else:
                        if not silent: self.parent.after(0, lambda: messagebox.showerror("Chyba", "Release nemá .exe soubor."))
                else:
                    if not silent: self.parent.after(0, lambda: messagebox.showinfo("Aktuální", "Máte nejnovější verzi."))
            else:
                if not silent: self.parent.after(0, lambda: messagebox.showerror("Chyba", f"GitHub API: {response.status_code}"))
        except Exception as e:
            if not silent: self.parent.after(0, lambda: messagebox.showerror("Chyba", f"{e}"))
        if on_continue: self.parent.after(0, on_continue)

    def _get_exe_info(self, release_data):
        for asset in release_data.get("assets", []):
            if asset["name"].endswith(".exe") and "Setup" not in asset["name"]: return asset["browser_download_url"], asset.get("size", 0)
            elif asset["name"].endswith(".exe"): return asset["browser_download_url"], asset.get("size", 0)
        return None, 0

    def _prompt_update(self, new_version, url, size, on_continue):
        msg = f"Je dostupná nová verze {new_version}!\n\nStáhnout a nainstalovat?\n(Aplikace se restartuje)"
        if messagebox.askyesno("Aktualizace", msg, parent=self.parent):
            # Předáme funkci, která přijme cestu k souboru
            UpdateProgressDialog(self.parent, size, url, self._perform_restart, on_continue)
        else:
            if on_continue: on_continue()

    def _perform_restart(self, downloaded_file_path):
        try:
            # Cesta k aktuálně běžící aplikaci (tu chceme přepsat)
            current_exe_path = Path(sys.executable).resolve()
            
            # Pokud běžíme ze skriptu (vývoj), jen simulujeme
            if not current_exe_path.name.lower().endswith(".exe"): 
                messagebox.showinfo("Dev Mode", f"Staženo do:\n{downloaded_file_path}\n(V Pythonu nelze přepsat běžící skript)")
                return

            # Cesta pro BAT soubor - také do TEMPU, aby nebyl vidět na ploše
            temp_dir = tempfile.gettempdir()
            bat_path = os.path.join(temp_dir, "ai_winget_updater.bat")
            
            # --- PROFESIONÁLNÍ BAT SKRIPT ---
            # 1. Čeká
            # 2. Smaže staré EXE
            # 3. Přesune nové EXE z Tempu na původní místo
            # 4. Vymaže _MEIPASS2 (řešení DLL chyby)
            # 5. Spustí aplikaci
            # 6. Smaže sám sebe (uklidí po sobě)
            
            bat_content = f"""
@echo off
chcp 65001 > nul
taskkill /F /PID {os.getpid()} > nul 2>&1
timeout /t 2 /nobreak > nul

:LOOP
del "{str(current_exe_path)}" 2>nul
if exist "{str(current_exe_path)}" (
    timeout /t 1 > nul
    goto LOOP
)

move /Y "{downloaded_file_path}" "{str(current_exe_path)}" > nul

set _MEIPASS2=
start "" "{str(current_exe_path)}"

(goto) 2>nul & del "%~f0"
"""
            with open(bat_path, "w", encoding="utf-8") as f:
                f.write(bat_content)

            # Spustíme BAT soubor skrytě (bez černého okna)
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            subprocess.Popen(str(bat_path), shell=True, startupinfo=startupinfo)
            
            # Okamžitě ukončíme Python, aby BAT mohl smazat soubor
            self.parent.quit()
            sys.exit()

        except Exception as e:
            messagebox.showerror("Chyba", f"Instalace selhala:\n{e}")