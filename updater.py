import sys
import os
import requests
import subprocess
import tempfile
import random
from pathlib import Path
from packaging import version

from PyQt6.QtCore import QObject, pyqtSignal, QThread, Qt
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar, QMessageBox, QPushButton

# Předpokládám existenci těchto proměnných v configu
from config import CURRENT_VERSION, COLORS

GITHUB_USER = "Vissse"
REPO_NAME = "Winget-Installer"

class DownloadWorker(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(str) # Path to file
    error = pyqtSignal(str)

    def __init__(self, url, total_size):
        super().__init__()
        self.url = url
        self.total_size = total_size
        self.is_running = True

    def run(self):
        try:
            temp_dir = tempfile.gettempdir()
            target_path = os.path.join(temp_dir, f"WingetInstaller_Update_{random.randint(1000,9999)}.exe")
            
            response = requests.get(self.url, stream=True)
            downloaded = 0
            
            with open(target_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if not self.is_running: break
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if self.total_size > 0:
                            percent = int((downloaded / self.total_size) * 100)
                            self.progress.emit(percent)
            
            if self.is_running:
                self.finished.emit(target_path)
        except Exception as e:
            self.error.emit(str(e))

    def stop(self):
        self.is_running = False

class UpdateDialog(QDialog):
    def __init__(self, parent, download_url, size, on_success):
        super().__init__(parent)
        self.setWindowTitle("Aktualizace aplikace")
        self.setFixedSize(400, 150)
        self.setStyleSheet(f"background-color: {COLORS.get('bg_main', '#1e1e1e')}; color: white;")
        
        layout = QVBoxLayout(self)
        
        self.lbl_status = QLabel("Stahuji aktualizaci...")
        self.lbl_status.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(self.lbl_status)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{ border: 1px solid #444; border-radius: 5px; text-align: center; }}
            QProgressBar::chunk {{ background-color: {COLORS.get('accent', '#0078d4')}; }}
        """)
        layout.addWidget(self.progress_bar)
        
        self.btn_cancel = QPushButton("Zrušit")
        self.btn_cancel.clicked.connect(self.cancel_download)
        self.btn_cancel.setStyleSheet("background-color: #d32f2f; color: white; border: none; padding: 5px; border-radius: 4px;")
        layout.addWidget(self.btn_cancel)

        self.on_success = on_success
        self.worker = DownloadWorker(download_url, size)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.finished.connect(self.on_download_finished)
        self.worker.error.connect(self.on_download_error)
        self.worker.start()

    def on_download_finished(self, path):
        self.accept()
        self.on_success(path)

    def on_download_error(self, err_msg):
        QMessageBox.critical(self, "Chyba", f"Stahování selhalo:\n{err_msg}")
        self.reject()

    def cancel_download(self):
        if self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
        self.reject()

class UpdateCheckerWorker(QThread):
    result = pyqtSignal(dict) # {status: 'ok'/'error', data: ...}

    def run(self):
        api_url = f"https://api.github.com/repos/{GITHUB_USER}/{REPO_NAME}/releases/latest"
        try:
            response = requests.get(api_url, timeout=5)
            if response.status_code == 200:
                self.result.emit({'status': 'ok', 'data': response.json()})
            else:
                self.result.emit({'status': 'error', 'msg': f"API Error: {response.status_code}"})
        except Exception as e:
            self.result.emit({'status': 'error', 'msg': str(e)})

class AppUpdater(QObject):
    def __init__(self, parent_window):
        super().__init__()
        self.parent = parent_window
        self.checker_worker = None

    def check_for_updates(self, silent=True):
        """
        silent=True: Nevyskakuje okno, pokud není update (pro start aplikace).
        silent=False: Vyskočí okno 'Máte nejnovější verzi' (pro tlačítko v nastavení).
        """
        self.silent_mode = silent
        self.checker_worker = UpdateCheckerWorker()
        self.checker_worker.result.connect(self.handle_check_result)
        self.checker_worker.start()

    def handle_check_result(self, result):
        if result['status'] == 'error':
            if not self.silent_mode:
                QMessageBox.warning(self.parent, "Chyba aktualizace", f"Nelze ověřit aktualizace:\n{result['msg']}")
            return

        data = result['data']
        latest_tag = data.get("tag_name", "0.0.0").lstrip("v")
        
        try:
            if version.parse(latest_tag) > version.parse(CURRENT_VERSION):
                asset_url, size = self._get_exe_info(data)
                if asset_url:
                    self._prompt_update(latest_tag, asset_url, size)
                elif not self.silent_mode:
                    QMessageBox.warning(self.parent, "Chyba", "Nová verze existuje, ale chybí .exe soubor.")
            else:
                if not self.silent_mode:
                    QMessageBox.information(self.parent, "Aktuální", f"Máte nejnovější verzi ({CURRENT_VERSION}).")
        except Exception as e:
            print(f"Update parse error: {e}")

    def _get_exe_info(self, release_data):
        for asset in release_data.get("assets", []):
            name = asset["name"].lower()
            if name.endswith(".exe"):
                return asset["browser_download_url"], asset.get("size", 0)
        return None, 0

    def _prompt_update(self, new_version, url, size):
        reply = QMessageBox.question(
            self.parent, 
            "Nová aktualizace", 
            f"Je dostupná nová verze {new_version}!\n\nChcete ji stáhnout a nainstalovat?\nAplikace se restartuje.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            dialog = UpdateDialog(self.parent, url, size, self._perform_restart)
            dialog.exec()

    def _perform_restart(self, downloaded_file_path):
        try:
            current_exe_path = Path(sys.executable).resolve()
            
            # Detekce dev prostředí
            if not str(current_exe_path).lower().endswith(".exe") or "python" in str(current_exe_path).lower():
                QMessageBox.information(self.parent, "Dev Mode", f"Staženo do:\n{downloaded_file_path}\n(V Pythonu nelze přepsat běžící skript)")
                return

            temp_dir = tempfile.gettempdir()
            bat_path = os.path.join(temp_dir, f"updater_winget_{random.randint(1000,9999)}.bat")
            
            clean_env = os.environ.copy()
            clean_env.pop('_MEIPASS2', None)
            
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

echo Restartuji aplikaci...
explorer.exe "{str(current_exe_path)}"

(goto) 2>nul & del "%~f0"
"""
            with open(bat_path, "w", encoding="utf-8") as f:
                f.write(bat_content)

            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            subprocess.Popen(str(bat_path), shell=True, env=clean_env, startupinfo=startupinfo)
            
            sys.exit()

        except Exception as e:
            QMessageBox.critical(self.parent, "Chyba", f"Instalace selhala:\n{e}")