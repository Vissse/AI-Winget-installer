# updater.py
import requests
import os
import sys
import subprocess
import tkinter as tk
from tkinter import messagebox, ttk
from packaging import version
import threading
import shutil
import tempfile
import random
from pathlib import Path

# --- KONFIGURACE GITHUB ---
GITHUB_USER = "Vissse"
REPO_NAME = "Winget-Installer"
CURRENT_VERSION = "4.3.20"

class UpdateProgressDialog(tk.Toplevel):
    def __init__(self, parent, total_size, download_url, on_success, on_fail):
        super().__init__(parent)
        self.title("Aktualizace aplikace")
        self.geometry("400x150")
        self.resizable(False, False)
        
        # Centr na obrazovku
        try:
            ws, hs = self.winfo_screenwidth(), self.winfo_screenheight()
            x, y = (ws/2) - (200), (hs/2) - (75)
            self.geometry(f"400x150+{int(x)}+{int(y)}")
        except: pass

        self.configure(bg="#1e1e1e")
        self.grab_set()

        self.lbl_info = tk.Label(self, text="Stahuji novou verzi...", font=("Segoe UI", 12, "bold"), 
                 bg="#1e1e1e", fg="white")
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

        threading.Thread(target=self.download_thread, daemon=True).start()

    def download_thread(self):
        new_exe_name = "new_version.exe"
        try:
            # 1. Úklid
            if os.path.exists(new_exe_name):
                try: os.remove(new_exe_name)
                except: pass

            # 2. Stahování
            response = requests.get(self.download_url, stream=True)
            downloaded = 0
            
            with open(new_exe_name, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if not self.is_downloading: break
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if self.total_size > 0:
                            percent = (downloaded / self.total_size) * 100
                            self.after(0, lambda p=percent: self.update_ui(p))
            
            # 3. Kontrola velikosti
            if self.total_size > 0 and downloaded < self.total_size:
                raise Exception("Stažený soubor je menší než očekáváno (chyba sítě).")

            self.after(0, self.on_success)
            self.after(0, self.destroy)

        except Exception as e:
            if os.path.exists(new_exe_name):
                try: os.remove(new_exe_name)
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
            print(f"Kontroluji update na: {self.api_url}")
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
                        if not silent: self.parent.after(0, lambda: messagebox.showerror("Chyba", "Chybí .exe soubor."))
                else:
                    if not silent: self.parent.after(0, lambda: messagebox.showinfo("Aktuální", "Máte nejnovější verzi."))
            else:
                if not silent: self.parent.after(0, lambda: messagebox.showerror("Chyba", f"GitHub API: {response.status_code}"))
        except Exception as e:
            if not silent: self.parent.after(0, lambda: messagebox.showerror("Chyba", f"{e}"))

        if on_continue:
            self.parent.after(0, on_continue)

    def _get_exe_info(self, release_data):
        for asset in release_data.get("assets", []):
            if asset["name"].endswith(".exe") and "Setup" not in asset["name"]:
                return asset["browser_download_url"], asset.get("size", 0)
            elif asset["name"].endswith(".exe"):
                 return asset["browser_download_url"], asset.get("size", 0)
        return None, 0

    def _prompt_update(self, new_version, url, size, on_continue):
        msg = f"Je dostupná nová verze {new_version}!\n\nChcete ji stáhnout a nainstalovat?\n(Aplikace se restartuje)"
        if messagebox.askyesno("Aktualizace", msg, parent=self.parent):
            UpdateProgressDialog(self.parent, size, url, self._perform_restart, on_continue)
        else:
            if on_continue: on_continue()

    def _perform_restart(self):
        try:
            # Převedeme cesty na Path objekty
            current_exe_path = Path(sys.executable).resolve()
            new_exe_path = Path("new_version.exe").resolve()
            
            # Fallback pro vývoj (pokud nejsme v exe)
            if not current_exe_path.name.lower().endswith(".exe"): 
                current_exe_path = Path("AI_Winget_Installer.exe").resolve()

            # =================================================================
            # 1. ZÁLOHA MEI (Podle vzoru s názvem "Winget")
            # =================================================================
            # PŘEJMENOVÁNO ze Struh na Winget
            safe_mei_path = Path(tempfile.gettempdir()) / f"Winget_Safe_MEI_{random.randint(1000, 99999)}"
            
            # Zkopírujeme běžící prostředí do bezpečí
            if hasattr(sys, '_MEIPASS'):
                current_mei = Path(sys._MEIPASS)
                try:
                    if safe_mei_path.exists():
                        shutil.rmtree(safe_mei_path, ignore_errors=True)
                    shutil.copytree(current_mei, safe_mei_path)
                    print(f"MEI uspesne zalohovano do: {safe_mei_path}")
                except Exception as copy_error:
                    print(f"Selhala zaloha MEI: {copy_error}")

            # Definice názvů pro BAT soubor - PŘEJMENOVÁNO
            bat_script_path = current_exe_path.parent / "updater_winget.bat"

            # =================================================================
            # 2. TVORBA BAT SKRIPTU
            # =================================================================
            
            # Přidáme safe_mei_path do PATH
            path_env_cmd = ""
            if safe_mei_path.exists():
                path_env_cmd = f'set "PATH=%PATH%;{str(safe_mei_path)}"'

            bat_content = f"""
@echo off
chcp 65001 > nul
echo Cekam na ukonceni aplikace...
timeout /t 2 /nobreak > nul

:LOOP
del "{str(current_exe_path)}" 2>nul
if exist "{str(current_exe_path)}" (
    timeout /t 1 > nul
    goto LOOP
)

echo Aktualizuji soubory...
move /Y "{str(new_exe_path)}" "{str(current_exe_path)}" > nul

echo Nastavuji bezpecne prostredi...
set _MEIPASS2=
{path_env_cmd}

echo Spoustim novou verzi...
start "" "{str(current_exe_path)}"

:: Úklid bat souboru
(goto) 2>nul & del "%~f0"
"""
            # Uložení BAT souboru
            with open(bat_script_path, "w", encoding="utf-8") as f:
                f.write(bat_content)

            # Spuštění BAT souboru
            subprocess.Popen(str(bat_script_path), shell=True)
            
            # Ukončení aplikace
            self.parent.quit()
            sys.exit()

        except Exception as e:
            messagebox.showerror("Chyba", f"Instalace selhala:\n{e}")