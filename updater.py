import sys
import os
import requests
import subprocess
import tempfile
import random
from pathlib import Path
from packaging import version

from PyQt6.QtCore import QObject, pyqtSignal, QThread, Qt, QTimer, QSize
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QProgressBar, 
                             QPushButton, QWidget, QApplication, QHBoxLayout, QGraphicsDropShadowEffect, QMessageBox)
from PyQt6.QtGui import QMouseEvent, QColor, QCursor

# Konfigurace
try:
    from config import CURRENT_VERSION, COLORS
except ImportError:
    CURRENT_VERSION = "0.0.0"
    COLORS = {'bg_main': '#1e1e1e', 'bg_sidebar': '#252526', 'accent': '#0078d4', 'text': '#ffffff', 'border': '#333', 'sub_text': '#aaaaaa'}

GITHUB_USER = "Vissse"
REPO_NAME = "Winget-Installer"

# ============================================================================
# 1. UI: MINIMALISTICKÝ DIALOG (CLEAN DESIGN)
# ============================================================================

class ModernMessageDialog(QDialog):
    def __init__(self, parent, title, message, btn_text="OK", show_cancel=False):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Velikost okna
        self.setFixedSize(420, 220)
        
        self.old_pos = None

        # Hlavní kontejner
        container = QWidget(self)
        container.setGeometry(10, 10, 400, 200) # Odsazení pro stín
        
        bg = COLORS.get('bg_sidebar', '#252526')
        border = COLORS.get('border', '#444')
        
        container.setStyleSheet(f"""
            QWidget {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 12px;
            }}
            QLabel {{ border: none; background: transparent; }}
        """)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(30, 25, 30, 25)
        layout.setSpacing(10)

        # 1. Nadpis
        lbl_title = QLabel(title)
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_title.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {COLORS.get('fg', 'white')};")
        layout.addWidget(lbl_title)
        
        # 2. Zpráva (Centrovaná)
        lbl_msg = QLabel(message)
        lbl_msg.setWordWrap(True)
        lbl_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_msg.setStyleSheet(f"font-size: 14px; color: {COLORS.get('sub_text', '#aaaaaa')}; margin-bottom: 5px;")
        layout.addWidget(lbl_msg)

        # 3. Tlačítka
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if show_cancel:
            btn_cancel = QPushButton("Zrušit")
            self._style_button(btn_cancel, primary=False)
            btn_cancel.clicked.connect(self.reject)
            btn_layout.addWidget(btn_cancel)

        btn_ok = QPushButton(btn_text)
        self._style_button(btn_ok, primary=True)
        btn_ok.clicked.connect(self.accept)
        btn_layout.addWidget(btn_ok)

        layout.addLayout(btn_layout)

        # Stín
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(25)
        shadow.setXOffset(0)
        shadow.setYOffset(8)
        shadow.setColor(QColor(0, 0, 0, 80))
        container.setGraphicsEffect(shadow)

    def _style_button(self, btn, primary=True):
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(32)
        btn.setMinimumWidth(80)
        
        accent = COLORS.get('accent', '#0078d4')
        accent_hover = COLORS.get('accent_hover', '#1f8ad2')
        border = COLORS.get('border', '#444')
        
        if primary:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {accent}; 
                    color: white; 
                    border: none; 
                    border-radius: 6px; 
                    font-weight: bold; 
                    font-size: 13px;
                }}
                QPushButton:hover {{ background-color: {accent_hover}; }}
            """)
        else:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent; 
                    color: {COLORS.get('sub_text', '#aaa')}; 
                    border: 1px solid {border}; 
                    border-radius: 6px; 
                    font-weight: bold; 
                    font-size: 13px;
                }}
                QPushButton:hover {{ 
                    background-color: {COLORS.get('item_hover', '#333')}; 
                    color: white; 
                }}
            """)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.old_pos:
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.pos() + delta)
            self.old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self.old_pos = None

# ============================================================================
# 2. UI: DIALOG STAHOVÁNÍ
# ============================================================================

class UpdateDownloadDialog(QDialog):
    def __init__(self, parent, url, size, on_success):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(420, 180)
        
        container = QWidget(self)
        container.setGeometry(10, 10, 400, 160)
        bg = COLORS.get('bg_sidebar', '#252526')
        
        container.setStyleSheet(f"""
            QWidget {{
                background-color: {bg};
                border: 1px solid {COLORS.get('border', '#444')};
                border-radius: 12px;
            }}
            QLabel {{ color: {COLORS.get('fg', 'white')}; border: none; background: transparent; }}
            QProgressBar {{ 
                border: 1px solid {COLORS.get('border', '#444')}; 
                background: {COLORS.get('input_bg', '#111')}; 
                height: 8px; border-radius: 4px; 
            }}
            QProgressBar::chunk {{ 
                background: {COLORS.get('accent', '#0078d4')}; border-radius: 4px; 
            }}
        """)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(15)
        
        self.lbl_info = QLabel("Stahuji aktualizaci...")
        self.lbl_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_info.setStyleSheet("font-weight: bold; font-size: 16px;")
        layout.addWidget(self.lbl_info)

        self.pbar = QProgressBar()
        self.pbar.setRange(0, 100)
        self.pbar.setTextVisible(False)  # <--- ZAJISTÍ, ŽE TEXT NEBUDE UVNITŘ BARU
        layout.addWidget(self.pbar)

        self.lbl_status = QLabel("0%")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # <--- ZMĚNA BARVY ZDE (použito COLORS.get('accent'))
        self.lbl_status.setStyleSheet(f"color: {COLORS.get('accent', '#0078d4')}; font-size: 14px; font-weight: bold;") 
        layout.addWidget(self.lbl_status)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(25)
        shadow.setColor(QColor(0, 0, 0, 80))
        container.setGraphicsEffect(shadow)

        self.on_success = on_success
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
        self.on_success(path)

    def download_error(self, err):
        dlg = ModernMessageDialog(self, "Chyba", str(err))
        dlg.exec()
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
# 3. HLAVNÍ CONTROLLER
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
                    assets = [a for a in data.get("assets", []) if a["name"].endswith(".exe")]
                    if assets:
                        proceed = False
                        self.prompt_update(tag, assets[0]["browser_download_url"], assets[0].get("size", 0))
                    else:
                        if not self.silent:
                            dlg = ModernMessageDialog(self.parent, "Chyba", "Nová verze nemá .exe soubor.")
                            dlg.exec()
                else:
                    if not self.silent:
                        dlg = ModernMessageDialog(
                            self.parent, 
                            "Jste aktuální", 
                            f"Verze {CURRENT_VERSION} je nejnovější.<br>Žádné aktualizace nejsou k dispozici."
                        )
                        dlg.exec()
            except Exception as e:
                print(e)
        
        elif res['status'] == 'error' and not self.silent:
             dlg = ModernMessageDialog(self.parent, "Chyba připojení", f"Nelze ověřit aktualizace.\n\n{res['msg']}")
             dlg.exec()

        if proceed and self.on_continue:
            self.on_continue()

    def prompt_update(self, ver, url, size):
        # Dialog s novým čistým designem
        dlg = ModernMessageDialog(
            self.parent, 
            "Nová aktualizace", 
            f"Je k dispozici nová verze {ver}.<br>Přejete si ji nainstalovat?",
            btn_text="Aktualizovat",
            show_cancel=True
        )
        
        if dlg.exec() == QDialog.DialogCode.Accepted:
            dl = UpdateDownloadDialog(self.parent, url, size, self.perform_restart_6_3_logic)
            dl.exec()
            if dl.result() == QDialog.DialogCode.Rejected and self.on_continue:
                self.on_continue()
        elif self.on_continue:
            self.on_continue()

    def perform_restart_6_3_logic(self, downloaded_file_path):
        try:
            current_exe_path = Path(sys.executable).resolve()
            if not str(current_exe_path).lower().endswith(".exe"):
                dlg = ModernMessageDialog(self.parent, "Dev Mode", f"Staženo do:\n{downloaded_file_path}")
                dlg.exec()
                return

            temp_dir = tempfile.gettempdir()
            bat_path = os.path.join(temp_dir, f"updater_winget_{random.randint(1000,9999)}.bat")
            
            clean_env = os.environ.copy()
            clean_env.pop('_MEIPASS2', None)
            clean_env.pop('_MEIPASS', None)
            
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
            
            subprocess.Popen(str(bat_path), shell=True, env=clean_env, startupinfo=startupinfo)
            QApplication.quit()
            sys.exit()

        except Exception as e:
            QMessageBox.critical(self.parent, "Chyba", f"Instalace selhala:\n{e}")