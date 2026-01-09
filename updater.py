import requests
import os
import sys
import subprocess
import tkinter as tk
from tkinter import messagebox, ttk
from packaging import version
import threading

# --- KONFIGURACE GITHUB ---
# Zde zadejte to VEŘEJNÉ repo, kam dáváte Releases (pokud jste zvolil variantu 2)
GITHUB_USER = "Vissse"       
REPO_NAME = "Winget-Installer"     
CURRENT_VERSION = "4.3.6"    

class UpdateProgressDialog(tk.Toplevel):
    """Okno s průběhem stahování"""
    def __init__(self, parent, total_size, download_url, on_complete):
        super().__init__(parent)
        self.title("Aktualizace aplikace")
        self.geometry("400x150")
        self.resizable(False, False)
        
        # Vynucení okna doprostřed
        try:
            ws, hs = self.winfo_screenwidth(), self.winfo_screenheight()
            x, y = (ws/2) - (200), (hs/2) - (75)
            self.geometry(f"400x150+{int(x)}+{int(y)}")
        except: pass

        self.configure(bg="#1e1e1e")
        self.grab_set() # Znemožní klikat jinam

        tk.Label(self, text="Stahuji novou verzi...", font=("Segoe UI", 12, "bold"), 
                 bg="#1e1e1e", fg="white").pack(pady=(20, 10))

        self.progress_var = tk.DoubleVar()
        self.progress = ttk.Progressbar(self, variable=self.progress_var, maximum=100)
        self.progress.pack(fill="x", padx=40, pady=10)

        self.status_lbl = tk.Label(self, text="0%", font=("Segoe UI", 10), bg="#1e1e1e", fg="#aaaaaa")
        self.status_lbl.pack()

        self.download_url = download_url
        self.total_size = total_size
        self.on_complete = on_complete
        self.is_downloading = True

        # Spustit stahování ve vlákně
        threading.Thread(target=self.download_thread, daemon=True).start()

    def download_thread(self):
        try:
            new_exe_name = "new_version.exe"
            response = requests.get(self.download_url, stream=True)
            downloaded = 0
            
            with open(new_exe_name, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if not self.is_downloading: break
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Výpočet procent
                        if self.total_size > 0:
                            percent = (downloaded / self.total_size) * 100
                            self.after(0, lambda p=percent: self.update_ui(p))

            self.after(0, self.on_complete)
            self.after(0, self.destroy)

        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Chyba", f"Stahování selhalo:\n{e}"))
            self.after(0, self.destroy)

    def update_ui(self, percent):
        self.progress_var.set(percent)
        self.status_lbl.config(text=f"{int(percent)} %")

class GitHubUpdater:
    def __init__(self, parent_window=None):
        self.parent = parent_window
        self.api_url = f"https://api.github.com/repos/{GITHUB_USER}/{REPO_NAME}/releases/latest"

    def check_for_updates(self, silent=False):
        """Zkontroluje, zda je na GitHubu novější verze."""
        try:
            print(f"Kontroluji update na: {self.api_url}")
            response = requests.get(self.api_url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                latest_tag = data.get("tag_name", "0.0.0").lstrip("v")
                
                if version.parse(latest_tag) > version.parse(CURRENT_VERSION):
                    asset_url, size = self._get_exe_info(data)
                    if asset_url:
                        self._prompt_update(latest_tag, asset_url, size, data.get("body", ""))
                    else:
                        if not silent: messagebox.showerror("Chyba", "Nová verze existuje, ale chybí .exe soubor.")
                else:
                    if not silent: messagebox.showinfo("Aktuální", "Máte nejnovější verzi.")
            else:
                if not silent: messagebox.showerror("Chyba", f"Nelze zjistit verzi (Kód {response.status_code}).\nZkontrolujte název repozitáře.")
                
        except Exception as e:
            print(f"Update error: {e}")
            if not silent: messagebox.showerror("Chyba", f"Chyba při kontrole aktualizací:\n{e}")

    def _get_exe_info(self, release_data):
        """Vrátí URL a velikost .exe souboru"""
        for asset in release_data.get("assets", []):
            if asset["name"].endswith(".exe"):
                return asset["browser_download_url"], asset.get("size", 0)
        return None, 0

    def _prompt_update(self, new_version, url, size, changelog):
        msg = f"Je dostupná nová verze {new_version}!\n\nChcete ji stáhnout a nainstalovat?\n(Aplikace se restartuje)"
        if messagebox.askyesno("Aktualizace", msg, parent=self.parent):
            # Spustíme vizuální stahování
            UpdateProgressDialog(self.parent, size, url, self._perform_restart)

    def _perform_restart(self):
        """Výměna souborů a restart (voláno až po stažení)"""
        try:
            current_exe = os.path.basename(sys.executable)
            if not current_exe.endswith(".exe"): current_exe = "AI_Winget_Installer.exe"

            bat_script = f"""
@echo off
timeout /t 2 > nul
del "{current_exe}"
move "new_version.exe" "{current_exe}"
start "" "{current_exe}"
del "%~f0"
"""
            with open("update_installer.bat", "w") as f:
                f.write(bat_script)

            subprocess.Popen("update_installer.bat", shell=True)
            sys.exit()

        except Exception as e:
            messagebox.showerror("Chyba", f"Instalace selhala:\n{e}")