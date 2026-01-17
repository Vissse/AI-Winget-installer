import sys
import os
import requests
import subprocess
import tempfile
import random
from pathlib import Path
from packaging import version

from PyQt6.QtCore import QObject, pyqtSignal, QThread, Qt, QPoint
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QProgressBar, QPushButton, QWidget, QFrame)
from PyQt6.QtGui import QMouseEvent

# Import barev pro styling
try:
    from config import CURRENT_VERSION, COLORS
except ImportError:
    # Fallback pokud config chybí (pro testování)
    CURRENT_VERSION = "1.0.0"
    COLORS = {
        'bg_sidebar': '#2b2b2b',
        'bg_main': '#1e1e1e',
        'accent': '#0078d4',
        'border': '#333333',
        'text': '#ffffff'
    }

GITHUB_USER = "Vissse"
REPO_NAME = "Winget-Installer"

# --- ZÁKLADNÍ STYLOVANÉ OKNO ---
class StyledDialogBase(QDialog):
    def __init__(self, parent=None, title="Update"):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        # Nastavíme pevnou velikost, ale umožníme resize pokud je třeba
        self.resize(450, 200) 
        self.old_pos = None

        # Hlavní layout okna (bez marginů, aby background filloval vše)
        self.window_layout = QVBoxLayout(self)
        self.window_layout.setContentsMargins(0, 0, 0, 0)
        self.window_layout.setSpacing(0)

        # Kontejner pro pozadí a rámeček
        self.container = QWidget(self)
        self.container.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS.get('bg_main', '#1e1e1e')};
                border: 1px solid {COLORS.get('border', '#444')};
                border-radius: 8px;
            }}
        """)
        self.window_layout.addWidget(self.container)

        # Layout uvnitř kontejneru
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(0)

        # 1. Horní lišta
        self.title_bar = QWidget()
        self.title_bar.setFixedHeight(40)
        self.title_bar.setStyleSheet(f"""
            background-color: {COLORS.get('bg_sidebar', '#252526')};
            border-bottom: 1px solid {COLORS.get('border', '#444')};
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            border-bottom-left-radius: 0px;
            border-bottom-right-radius: 0px;
        """)
        
        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(15, 0, 10, 0)
        
        self.lbl_title = QLabel(title)
        self.lbl_title.setStyleSheet("color: white; font-weight: bold; font-size: 13px; border: none; background: transparent;")
        title_layout.addWidget(self.lbl_title)
        title_layout.addStretch()
        
        self.btn_close = QPushButton("✕")
        self.btn_close.setFixedSize(30, 30)
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.clicked.connect(self.reject)
        self.btn_close.setStyleSheet("""
            QPushButton { background: transparent; color: #aaa; border: none; font-weight: bold; }
            QPushButton:hover { color: white; background-color: #c42b1c; border-radius: 4px; }
        """)
        title_layout.addWidget(self.btn_close)
        
        self.container_layout.addWidget(self.title_bar)

        # 2. Obsah (Content Widget)
        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background: transparent; border: none;")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(20, 20, 20, 20)
        
        self.container_layout.addWidget(self.content_widget)


# --- DIALOG PRO POTVRZENÍ AKTUALIZACE ---
class UpdatePromptDialog(StyledDialogBase):
    def __init__(self, parent, new_version):
        # Odstraněny parametry on_yes/on_no, nejsou potřeba
        super().__init__(parent, title="Dostupná aktualizace")
        
        lbl_info = QLabel(f"Byla nalezena nová verze <b>{new_version}</b>.<br><br>Chcete ji nyní stáhnout a nainstalovat?<br>(Aplikace se restartuje)")
        lbl_info.setWordWrap(True)
        lbl_info.setStyleSheet("color: #ddd; font-size: 14px; border: none;")
        self.content_layout.addWidget(lbl_info)
        self.content_layout.addStretch()

        btn_layout = QHBoxLayout()
        
        btn_later = QPushButton("Později")
        btn_later.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_later.setFixedHeight(35)
        # Tlačítko Později prostě zavře dialog s kódem Rejected
        btn_later.clicked.connect(self.reject) 
        btn_later.setStyleSheet(f"background-color: transparent; border: 1px solid #555; color: #ddd; border-radius: 4px;")
        
        btn_update = QPushButton("Aktualizovat")
        btn_update.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_update.setFixedHeight(35)
        # Tlačítko Aktualizovat zavře dialog s kódem Accepted
        btn_update.clicked.connect(self.accept)
        btn_update.setStyleSheet(f"background-color: {COLORS.get('accent', '#0078d4')}; color: white; border: none; border-radius: 4px; font-weight: bold;")
        
        btn_layout.addWidget(btn_later)
        btn_layout.addWidget(btn_update)
        self.content_layout.addLayout(btn_layout)

    def accept_update(self):
        self.accept()
        self.on_yes()
    
    def reject(self):
        super().reject()
        self.on_no()

# --- DIALOG PRO STAHOVÁNÍ ---
class UpdateDownloadDialog(StyledDialogBase):
    def __init__(self, parent, download_url, size, on_success):
        super().__init__(parent, title="Stahování aktualizace")
        self.setFixedSize(400, 200)
        self.on_success = on_success
        
        self.lbl_status = QLabel("Stahuji data...")
        self.lbl_status.setStyleSheet("color: white; font-size: 14px; border: none;")
        self.content_layout.addWidget(self.lbl_status)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{ border: 1px solid #444; border-radius: 4px; background-color: #111; text-align: center; color: white; height: 20px; }}
            QProgressBar::chunk {{ background-color: {COLORS.get('accent', '#0078d4')}; border-radius: 3px; }}
        """)
        self.content_layout.addWidget(self.progress_bar)
        self.content_layout.addStretch()
        
        self.btn_cancel = QPushButton("Zrušit")
        self.btn_cancel.setFixedSize(100, 30)
        self.btn_cancel.clicked.connect(self.cancel_download)
        self.btn_cancel.setStyleSheet("background-color: #d32f2f; color: white; border: none; border-radius: 4px;")
        self.content_layout.addWidget(self.btn_cancel, alignment=Qt.AlignmentFlag.AlignCenter)

        # Start download
        self.worker = DownloadWorker(download_url, size)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.finished.connect(self.on_download_finished)
        self.worker.error.connect(self.on_download_error)
        self.worker.start()

    def on_download_finished(self, path):
        self.lbl_status.setText("Stahování dokončeno.")
        self.accept()
        self.on_success(path)

    def on_download_error(self, err_msg):
        self.lbl_status.setText(f"Chyba: {err_msg}")
        self.btn_cancel.setText("Zavřít")

    def cancel_download(self):
        if self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
        self.reject()

# --- WORKERS (Beze změny logiky) ---
class DownloadWorker(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(str) 
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
            if self.is_running: self.finished.emit(target_path)
        except Exception as e:
            self.error.emit(str(e))

    def stop(self): self.is_running = False

class UpdateCheckerWorker(QThread):
    result = pyqtSignal(dict) 

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

# --- HLAVNÍ TŘÍDA UPDATERU ---
class AppUpdater(QObject):
    def __init__(self, parent_window):
        super().__init__()
        self.parent = parent_window
        self.checker_worker = None
        self.on_continue_callback = None # Co dělat, když není update

    def check_for_updates(self, silent=True, on_continue=None):
        """
        silent: True = start aplikace (nic neukazuj, když není update)
        on_continue: Funkce, která se zavolá, pokud se neaktualizuje (tj. spustí se hlavní okno)
        """
        self.silent_mode = silent
        self.on_continue_callback = on_continue
        
        self.checker_worker = UpdateCheckerWorker()
        self.checker_worker.result.connect(self.handle_check_result)
        self.checker_worker.start()

    def handle_check_result(self, result):
        if result['status'] == 'error':
            if not self.silent_mode:
                self._show_msg("Chyba aktualizace", f"Nelze ověřit aktualizace:\n{result['msg']}")
            self._continue_flow()
            return

        data = result['data']
        latest_tag = data.get("tag_name", "0.0.0").lstrip("v")
        
        try:
            if version.parse(latest_tag) > version.parse(CURRENT_VERSION):
                asset_url, size = self._get_exe_info(data)
                if asset_url:
                    # MÁME UPDATE -> Zobrazíme Custom Dialog
                    self._show_update_prompt(latest_tag, asset_url, size)
                else:
                    if not self.silent_mode:
                        self._show_msg("Chyba", "Nová verze existuje, ale chybí .exe soubor.")
                    self._continue_flow()
            else:
                if not self.silent_mode:
                    self._show_msg("Aktuální", f"Máte nejnovější verzi ({CURRENT_VERSION}).")
                self._continue_flow()
        except Exception as e:
            print(f"Update parse error: {e}")
            self._continue_flow()

    def _continue_flow(self):
        """Pokud je nastaven callback (start programu), zavoláme ho."""
        if self.on_continue_callback:
            self.on_continue_callback()

    def _show_msg(self, title, text):
        dlg = StyledDialogBase(self.parent, title)
        # Nastavíme menší výšku pro jednoduchou zprávu, aby to nevypadalo prázdně
        dlg.setFixedSize(400, 180) 
        
        lbl = QLabel(text)
        lbl.setStyleSheet("color: white; font-size: 14px; border: none;")
        lbl.setWordWrap(True)
        lbl.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
        # Přidáme label do layoutu
        dlg.content_layout.addWidget(lbl)
        dlg.content_layout.addStretch() # Tlačí tlačítko dolů

        btn = QPushButton("OK")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(dlg.accept)
        btn.setFixedSize(80, 30)
        btn.setStyleSheet(f"""
            QPushButton {{ 
                background-color: {COLORS.get('accent', '#0078d4')}; 
                color: white; 
                border: none; 
                border-radius: 4px; 
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {COLORS.get('accent_hover', '#0099ff')}; }}
        """)
        
        # Zarovnání tlačítka doprava
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(btn)
        
        dlg.content_layout.addLayout(btn_layout)
        dlg.exec()

    def _show_update_prompt(self, ver, url, size):
        # Vytvoříme dialog
        dialog = UpdatePromptDialog(self.parent, ver)
        
        # Spustíme ho a čekáme na výsledek (blokuje kód, dokud uživatel neklikne)
        result = dialog.exec()
        
        if result == QDialog.DialogCode.Accepted:
            # Uživatel klikl na "Aktualizovat"
            self._start_download(url, size)
        else:
            # Uživatel klikl na "Později" NEBO zavřel okno křížkem (Rejected)
            self._continue_flow()

    def _start_download(self, url, size):
        # Dialog pro stahování
        dl_dialog = UpdateDownloadDialog(self.parent, url, size, self._perform_restart)
        dl_dialog.exec()
        
        # Pokud se stahování dokončí úspěšně, zavolá se _perform_restart a aplikace se ukončí.
        # Pokud se kód dostane sem, znamená to, že uživatel stahování zrušil (klikl na Zrušit/Křížek).
        # V tom případě musíme normálně spustit aplikaci.
        if dl_dialog.result() == QDialog.DialogCode.Rejected:
            self._continue_flow()

    def _get_exe_info(self, release_data):
        for asset in release_data.get("assets", []):
            if asset["name"].lower().endswith(".exe"):
                return asset["browser_download_url"], asset.get("size", 0)
        return None, 0

    def _perform_restart(self, downloaded_file_path):
        try:
            current_exe_path = Path(sys.executable).resolve()
            if not str(current_exe_path).lower().endswith(".exe") or "python" in str(current_exe_path).lower():
                self._show_msg("Dev Mode", f"Staženo do:\n{downloaded_file_path}\n(Nelze restartovat Python skript)")
                self._continue_flow()
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
explorer.exe "{str(current_exe_path)}"
(goto) 2>nul & del "%~f0"
"""
            with open(bat_path, "w", encoding="utf-8") as f: f.write(bat_content)
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            subprocess.Popen(str(bat_path), shell=True, env=clean_env, startupinfo=startupinfo)
            sys.exit()
        except Exception as e:
            self._show_msg("Chyba", f"Restart selhal:\n{e}")