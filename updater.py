import sys
import os
import requests
import subprocess
import tempfile
import random
from pathlib import Path
from packaging import version

from PyQt6.QtCore import QObject, pyqtSignal, QThread, Qt, QTimer, QPoint
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QProgressBar, QPushButton, QWidget, QFrame, QApplication)
from PyQt6.QtGui import QColor, QScreen

# Import konfigurace
try:
    from config import CURRENT_VERSION, COLORS
except ImportError:
    CURRENT_VERSION = "0.0.0"
    COLORS = {
        'bg_sidebar': '#2b2b2b', 'bg_main': '#1e1e1e', 'accent': '#0078d4', 'border': '#333333', 'text': '#ffffff'
    }

GITHUB_USER = "Vissse"
REPO_NAME = "Winget-Installer"

# --- 1. TOAST NOTIFIKACE (Vypadá jako na vašem obrázku) ---
class StatusToast(QDialog):
    """
    Neblokující bublina, která se zobrazí a po chvíli sama zmizí.
    Vypadá přesně jako 'Aktuální' box na vašem screenu.
    """
    def __init__(self, parent, title, message, duration=3000):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.ToolTip | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(300, 80)
        
        # Styl kontejneru (Tmavě šedá, lehký border)
        self.container = QWidget(self)
        self.container.setGeometry(0, 0, 300, 80)
        self.container.setStyleSheet(f"""
            QWidget {{
                background-color: #2d2d2d; 
                border: 1px solid #454545;
                border-radius: 4px;
            }}
        """)
        
        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(2)
        
        # Nadpis (např. "Aktuální")
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 13px; border: none;")
        layout.addWidget(lbl_title)
        
        # Zpráva (např. "Máte nejnovější verzi...")
        lbl_msg = QLabel(message)
        lbl_msg.setStyleSheet("color: #cccccc; font-size: 11px; border: none;")
        layout.addWidget(lbl_msg)
        
        # Animace zmizení
        self.duration = duration
        QTimer.singleShot(self.duration, self.fade_out)
        
        # Pozicování - Zobrazí se uprostřed nad parent oknem nebo u myši
        self.center_on_parent(parent)

    def center_on_parent(self, parent):
        if parent:
            geo = parent.geometry()
            # Umístíme to doprostřed okna
            x = geo.x() + (geo.width() - self.width()) // 2
            y = geo.y() + (geo.height() - self.height()) // 2
            self.move(x, y)
        else:
            # Fallback na střed obrazovky
            screen = QApplication.primaryScreen().geometry()
            self.move((screen.width() - self.width()) // 2, (screen.height() - self.height()) // 2)

    def fade_out(self):
        self.close()

# --- 2. UPDATE DIALOGY (Pro případ, že JE update) ---

class StyledDialogBase(QDialog):
    """Základní okno pro update dialogy"""
    def __init__(self, parent=None, title="Update"):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(450, 220) 

        self.window_layout = QVBoxLayout(self)
        self.window_layout.setContentsMargins(0, 0, 0, 0)
        
        self.container = QWidget(self)
        self.container.setStyleSheet(f"background-color: {COLORS.get('bg_main', '#1e1e1e')}; border: 1px solid {COLORS.get('border', '#444')}; border-radius: 8px;")
        self.window_layout.addWidget(self.container)
        
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)

        # Lišta
        title_bar = QWidget()
        title_bar.setFixedHeight(40)
        title_bar.setStyleSheet(f"background-color: {COLORS.get('bg_sidebar', '#252526')}; border-bottom: 1px solid #444; border-top-left-radius: 8px; border-top-right-radius: 8px;")
        t_layout = QHBoxLayout(title_bar)
        t_layout.setContentsMargins(15, 0, 10, 0)
        
        lbl = QLabel(title)
        lbl.setStyleSheet("color: white; font-weight: bold; border: none; background: transparent;")
        t_layout.addWidget(lbl)
        t_layout.addStretch()
        
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(30, 30)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.reject)
        close_btn.setStyleSheet("QPushButton { background: transparent; color: #aaa; border: none; } QPushButton:hover { color: white; background: #c42b1c; border-radius: 4px; }")
        t_layout.addWidget(close_btn)
        
        self.container_layout.addWidget(title_bar)
        
        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background: transparent; border: none;")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(20, 20, 20, 20)
        self.container_layout.addWidget(self.content_widget)

class UpdatePromptDialog(StyledDialogBase):
    def __init__(self, parent, new_version):
        super().__init__(parent, title="Dostupná aktualizace")
        lbl = QLabel(f"Byla nalezena nová verze <b>{new_version}</b>.<br><br>Chcete ji nyní stáhnout a nainstalovat?<br><span style='color:#888'>(Aplikace se restartuje)</span>")
        lbl.setWordWrap(True)
        lbl.setStyleSheet("color: #ddd; font-size: 14px; border: none;")
        self.content_layout.addWidget(lbl)
        self.content_layout.addStretch()
        
        btns = QHBoxLayout()
        btn_no = QPushButton("Později")
        btn_no.clicked.connect(self.reject)
        btn_no.setStyleSheet("background: transparent; border: 1px solid #555; color: #ddd; border-radius: 4px; padding: 6px 15px;")
        
        btn_yes = QPushButton("Aktualizovat")
        btn_yes.clicked.connect(self.accept)
        btn_yes.setStyleSheet(f"background: {COLORS.get('accent', '#0078d4')}; color: white; border: none; border-radius: 4px; padding: 6px 15px; font-weight: bold;")
        
        btns.addWidget(btn_no)
        btns.addWidget(btn_yes)
        self.content_layout.addLayout(btns)

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
            if os.path.exists(target_path): os.remove(target_path)

            response = requests.get(self.url, stream=True)
            downloaded = 0
            with open(target_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if not self.is_running: break
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if self.total_size > 0:
                            self.progress.emit(int((downloaded / self.total_size) * 100))
            if self.is_running: self.finished.emit(target_path)
        except Exception as e:
            self.error.emit(str(e))

    def stop(self): self.is_running = False

class UpdateDownloadDialog(StyledDialogBase):
    def __init__(self, parent, url, size, on_success):
        super().__init__(parent, title="Stahování")
        self.setFixedSize(400, 180)
        self.on_success = on_success
        
        self.lbl_status = QLabel("Stahuji aktualizaci...")
        self.lbl_status.setStyleSheet("color: white; border: none;")
        self.content_layout.addWidget(self.lbl_status)
        
        self.pbar = QProgressBar()
        self.pbar.setStyleSheet(f"QProgressBar {{ border: 1px solid #444; background: #111; height: 10px; border-radius: 5px; }} QProgressBar::chunk {{ background: {COLORS.get('accent', '#0078d4')}; border-radius: 4px; }}")
        self.content_layout.addWidget(self.pbar)
        
        self.btn_cancel = QPushButton("Zrušit")
        self.btn_cancel.clicked.connect(self.cancel)
        self.btn_cancel.setStyleSheet("color: #aaa; background: transparent; border: none;")
        self.content_layout.addWidget(self.btn_cancel, alignment=Qt.AlignmentFlag.AlignCenter)
        
        self.worker = DownloadWorker(url, size)
        self.worker.progress.connect(self.pbar.setValue)
        self.worker.finished.connect(self.done)
        self.worker.error.connect(lambda e: self.lbl_status.setText(f"Chyba: {e}"))
        self.worker.start()

    def done(self, path):
        self.accept()
        self.on_success(path)

    def cancel(self):
        self.worker.stop()
        self.reject()

class UpdateCheckerWorker(QThread):
    result = pyqtSignal(dict)
    def run(self):
        try:
            r = requests.get(f"https://api.github.com/repos/{GITHUB_USER}/{REPO_NAME}/releases/latest", timeout=5)
            if r.status_code == 200: self.result.emit({'status': 'ok', 'data': r.json()})
            else: self.result.emit({'status': 'error', 'msg': str(r.status_code)})
        except Exception as e: self.result.emit({'status': 'error', 'msg': str(e)})

# --- 3. HLAVNÍ LOGIKA (S OPRAVENÝM RESTARTEM) ---

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
                # Logika: Pokud je na GitHubu novější verze
                if version.parse(tag) > version.parse(CURRENT_VERSION):
                    assets = [a for a in data.get("assets", []) if a["name"].endswith(".exe")]
                    if assets:
                        proceed = False
                        self.prompt_update(tag, assets[0]["browser_download_url"], assets[0].get("size", 0))
                else:
                    # NENÍ UPDATE -> ZOBRAZIT TOAST (pokud to není silent start)
                    if not self.silent:
                        self.show_toast("Aktuální", f"Máte nejnovější verzi ({CURRENT_VERSION}).")
            except Exception as e:
                print(e)
        
        if proceed and self.on_continue:
            self.on_continue()

    def show_toast(self, title, msg):
        # Vytvoříme a zobrazíme Toast notifikaci
        toast = StatusToast(self.parent, title, msg)
        toast.show()

    def prompt_update(self, ver, url, size):
        dlg = UpdatePromptDialog(self.parent, ver)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            dl = UpdateDownloadDialog(self.parent, url, size, self.perform_restart)
            dl.exec()
            if dl.result() == QDialog.DialogCode.Rejected and self.on_continue:
                self.on_continue()
        elif self.on_continue:
            self.on_continue()

    def perform_restart(self, new_exe):
        """
        ZDE JE TA ZÁSADNÍ OPRAVA:
        Používáme explorer.exe breakaway metodu z vašeho starého kódu.
        To zajistí čistý start nové verze bez závislostí na starém procesu.
        """
        try:
            current_exe = Path(sys.executable).resolve()
            
            # Detekce dev prostředí vs build
            if not str(current_exe).lower().endswith(".exe"):
                print(f"Dev mode update sim: {new_exe}")
                if self.on_continue: self.on_continue()
                return

            temp_dir = tempfile.gettempdir()
            bat_path = os.path.join(temp_dir, f"updater_winget_{random.randint(1000,9999)}.bat")
            
            # Čištění prostředí od PyInstalleru (kritické pro update!)
            clean_env = os.environ.copy()
            clean_env.pop('_MEIPASS2', None)
            clean_env.pop('_MEIPASS', None)

            # Bat skript z vašeho původního souboru
            bat_content = f"""
@echo off
chcp 65001 > nul
taskkill /F /PID {os.getpid()} > nul 2>&1
timeout /t 2 /nobreak > nul

:LOOP
del "{str(current_exe)}" 2>nul
if exist "{str(current_exe)}" (
    timeout /t 1 > nul
    goto LOOP
)

move /Y "{new_exe}" "{str(current_exe)}" > nul

echo Spoustim pres Explorer...
explorer.exe "{str(current_exe)}"

(goto) 2>nul & del "%~f0"
"""
            with open(bat_path, "w", encoding="utf-8") as f: f.write(bat_content)
            
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            subprocess.Popen(str(bat_path), shell=True, env=clean_env, startupinfo=startupinfo)
            sys.exit() # Okamžité ukončení
            
        except Exception as e:
            print(f"Restart failed: {e}")
            if self.on_continue: self.on_continue()