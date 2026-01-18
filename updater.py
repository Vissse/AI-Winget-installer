import sys
import os
import requests
import subprocess
import tempfile
import random
from pathlib import Path
from packaging import version

from PyQt6.QtCore import QObject, pyqtSignal, QThread, Qt
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QProgressBar, 
                             QPushButton, QWidget, QApplication, QMessageBox)

# Konfigurace
try:
    from config import CURRENT_VERSION, COLORS
except ImportError:
    CURRENT_VERSION = "0.0.0"
    COLORS = {'bg_main': '#1e1e1e', 'accent': '#0078d4', 'text': '#ffffff'}

GITHUB_USER = "Vissse"
REPO_NAME = "Winget-Installer"

# ============================================================================
# 1. UI: DIALOG STAHOVÁNÍ (Vzhled PyQt, ale chování jako ve v6.3)
# ============================================================================

class UpdateDownloadDialog(QDialog):
    def __init__(self, parent, url, size, on_success):
        super().__init__(parent)
        self.setWindowTitle("Aktualizace aplikace")
        self.setFixedSize(400, 150)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint)
        
        # Stylování
        self.setStyleSheet(f"""
            QDialog {{ background-color: {COLORS.get('bg_main', '#1e1e1e')}; color: white; }}
            QLabel {{ color: white; }}
            QProgressBar {{ border: 1px solid #444; background: #111; height: 10px; border-radius: 5px; }}
            QProgressBar::chunk {{ background: {COLORS.get('accent', '#0078d4')}; border-radius: 4px; }}
        """)

        layout = QVBoxLayout(self)
        
        self.lbl_info = QLabel("Stahuji aktualizaci...")
        self.lbl_info.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(self.lbl_info)

        self.pbar = QProgressBar()
        self.pbar.setRange(0, 100)
        layout.addWidget(self.pbar)

        self.lbl_status = QLabel("0%")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_status)

        self.on_success = on_success
        self.url = url
        self.total_size = size
        
        # Spuštění stahování
        self.worker = DownloadWorker(url, size)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.download_finished)
        self.worker.error.connect(self.download_error)
        self.worker.start()

    def update_progress(self, val):
        self.pbar.setValue(val)
        self.lbl_status.setText(f"{val} %")

    def download_finished(self, path):
        self.accept()
        # Předáme cestu ke staženému souboru dál
        self.on_success(path)

    def download_error(self, err):
        QMessageBox.critical(self, "Chyba", f"Stahování selhalo:\n{err}")
        self.reject()

class DownloadWorker(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, url, total_size):
        super().__init__()
        self.url = url
        self.total_size = total_size

    def run(self):
        try:
            # Stahujeme do TEMPU, stejně jako ve verzi 6.3
            temp_dir = tempfile.gettempdir()
            target_path = os.path.join(temp_dir, f"WingetInstaller_Update_{random.randint(1000,9999)}.exe")

            if os.path.exists(target_path):
                try: os.remove(target_path)
                except: pass

            response = requests.get(self.url, stream=True, timeout=15)
            if response.status_code != 200:
                raise Exception(f"HTTP Chyba: {response.status_code}")

            downloaded = 0
            with open(target_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if self.total_size > 0:
                            self.progress.emit(int((downloaded / self.total_size) * 100))

            self.finished.emit(target_path)
        except Exception as e:
            self.error.emit(str(e))

class UpdateCheckerWorker(QThread):
    result = pyqtSignal(dict)
    def run(self):
        try:
            r = requests.get(f"https://api.github.com/repos/{GITHUB_USER}/{REPO_NAME}/releases/latest", timeout=5)
            if r.status_code == 200: 
                self.result.emit({'status': 'ok', 'data': r.json()})
            else: 
                self.result.emit({'status': 'error', 'msg': str(r.status_code)})
        except Exception as e: 
            self.result.emit({'status': 'error', 'msg': str(e)})

# ============================================================================
# 2. HLAVNÍ CONTROLLER (Logika 6.3)
# ============================================================================

class AppUpdater(QObject):
    def __init__(self, parent_window):
        super().__init__()
        self.parent = parent_window
        self.on_continue = None

    def check_for_updates(self, silent=True, on_continue=None):
        self.silent = silent
        self.on_continue = on_continue
        
        self.worker = UpdateCheckerWorker()
        self.worker.result.connect(self.handle_result)
        self.worker.start()

    def handle_result(self, res):
        proceed = True
        if res['status'] == 'ok':
            data = res['data']
            tag = data.get("tag_name", "0.0.0").lstrip("v")
            
            try:
                if version.parse(tag) > version.parse(CURRENT_VERSION):
                    # Hledáme .exe (ne .zip, vracíme se k EXE)
                    assets = [a for a in data.get("assets", []) if a["name"].endswith(".exe")]
                    if assets:
                        proceed = False
                        self.prompt_update(tag, assets[0]["browser_download_url"], assets[0].get("size", 0))
                    else:
                        if not self.silent:
                            QMessageBox.warning(self.parent, "Chyba", "Nová verze nemá .exe soubor.")
                else:
                    if not self.silent:
                        QMessageBox.information(self.parent, "Aktuální", f"Verze {CURRENT_VERSION} je aktuální.")
            except Exception as e:
                print(e)
        
        if proceed and self.on_continue:
            self.on_continue()

    def prompt_update(self, ver, url, size):
        reply = QMessageBox.question(
            self.parent, 
            "Aktualizace", 
            f"Je dostupná nová verze {ver}!\n\nChcete ji stáhnout a nainstalovat?\n(Aplikace se restartuje)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            dl = UpdateDownloadDialog(self.parent, url, size, self.perform_restart_6_3_logic)
            dl.exec()
            # Pokud uživatel zavře dialog křížkem, aplikace pokračuje
            if dl.result() == QDialog.DialogCode.Rejected and self.on_continue:
                self.on_continue()
        elif self.on_continue:
            self.on_continue()

    def perform_restart_6_3_logic(self, downloaded_file_path):
        """
        TOTÁLNÍ KOPIE LOGIKY Z VERZE 6.3
        Tohle je ten mechanismus, který fungoval.
        """
        try:
            current_exe_path = Path(sys.executable).resolve()
            
            # Kontrola pro dev prostředí
            if not str(current_exe_path).lower().endswith(".exe"):
                QMessageBox.information(self.parent, "Dev Mode", f"Staženo do:\n{downloaded_file_path}\n(V Python scriptu nelze přepsat běžící proces)")
                return

            temp_dir = tempfile.gettempdir()
            bat_path = os.path.join(temp_dir, f"updater_winget_{random.randint(1000,9999)}.bat")
            
            # Čištění environment proměnných (Důležité pro OneFile!)
            clean_env = os.environ.copy()
            clean_env.pop('_MEIPASS2', None)
            clean_env.pop('_MEIPASS', None)
            
            # --- MAGICKÝ BAT SKRIPT Z VERZE 6.3 ---
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

echo Spoustim pres Explorer (Breakaway)...
explorer.exe "{str(current_exe_path)}"

(goto) 2>nul & del "%~f0"
"""
            with open(bat_path, "w", encoding="utf-8") as f:
                f.write(bat_content)

            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            # Spustíme BAT a odpojíme se
            subprocess.Popen(str(bat_path), shell=True, env=clean_env, startupinfo=startupinfo)
            
            # Ukončíme Python
            QApplication.quit()
            sys.exit()

        except Exception as e:
            QMessageBox.critical(self.parent, "Chyba", f"Instalace selhala:\n{e}")