import requests
import os
import sys
import subprocess
import tkinter as tk
from tkinter import messagebox
from packaging import version

# --- KONFIGURACE GITHUB ---
GITHUB_USER = "Vissse"  
REPO_NAME = "Winget-Installer"
CURRENT_VERSION = "4.3.2"  # <-- TOTO MUSÍTE ZVEDAT PŘI KAŽDÉM UPDATE

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
                latest_tag = data.get("tag_name", "0.0.0").lstrip("v") # Odstraní 'v' pokud tam je
                
                # Porovnání verzí
                if version.parse(latest_tag) > version.parse(CURRENT_VERSION):
                    # Je dostupná nová verze!
                    download_url = self._get_exe_asset_url(data)
                    if download_url:
                        self._prompt_update(latest_tag, download_url, data.get("body", ""))
                    else:
                        if not silent: messagebox.showerror("Chyba", "Nová verze existuje, ale chybí .exe soubor v Release.")
                else:
                    if not silent: messagebox.showinfo("Aktuální", "Máte nejnovější verzi.")
            else:
                if not silent: messagebox.showerror("Chyba", "Nelze zjistit verzi z GitHubu.")
                
        except Exception as e:
            print(f"Update error: {e}")
            if not silent: messagebox.showerror("Chyba", f"Chyba při kontrole aktualizací:\n{e}")

    def _get_exe_asset_url(self, release_data):
        """Najde v Release assets soubor s koncovkou .exe"""
        for asset in release_data.get("assets", []):
            if asset["name"].endswith(".exe"):
                return asset["browser_download_url"]
        return None

    def _prompt_update(self, new_version, url, changelog):
        """Zobrazí dialog a zeptá se uživatele."""
        msg = f"Je dostupná nová verze {new_version}!\n\nChcete ji stáhnout a nainstalovat?\n(Aplikace se restartuje)"
        if messagebox.askyesno("Aktualizace", msg, parent=self.parent):
            self._perform_update(url)

    def _perform_update(self, url):
        """Stáhne soubor a spustí výměnu."""
        try:
            # 1. Stáhnout novou verzi
            new_exe_name = "new_version.exe"
            response = requests.get(url, stream=True)
            with open(new_exe_name, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # 2. Vytvořit aktualizační BAT skript
            current_exe = os.path.basename(sys.executable)
            
            # Pokud běžíme ve skriptu (ne v exe), jen simulujeme
            if not current_exe.endswith(".exe"):
                current_exe = "AI_Winget_Installer.exe" # Fallback název

            bat_script = f"""
@echo off
timeout /t 2 > nul
del "{current_exe}"
move "{new_exe_name}" "{current_exe}"
start "" "{current_exe}"
del "%~f0"
"""
            with open("update_installer.bat", "w") as f:
                f.write(bat_script)

            # 3. Spustit BAT a ukončit tuto aplikaci
            subprocess.Popen("update_installer.bat", shell=True)
            sys.exit()

        except Exception as e:
            messagebox.showerror("Chyba", f"Aktualizace selhala:\n{e}")