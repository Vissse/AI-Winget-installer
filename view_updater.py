import subprocess
import re
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QListWidget, QListWidgetItem, 
                             QProgressBar, QTextEdit, QFrame)
from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal
from PyQt6.QtGui import QColor

from config import COLORS

# --- 1. WORKER PRO SKENOVÁNÍ ---
class ScanWorker(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def run(self):
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            cmd = "winget upgrade --include-unknown --accept-source-agreements"
            result = subprocess.run(cmd, capture_output=True, text=True, startupinfo=startupinfo, encoding='utf-8', errors='replace')
            lines = result.stdout.split('\n')
            updates = []
            start_parsing = False
            for line in lines:
                if line.startswith("Name") and "Id" in line:
                    start_parsing = True
                    continue
                if not start_parsing or "----" in line or not line.strip(): 
                    continue
                parts = re.split(r'\s{2,}', line.strip())
                if len(parts) >= 4:
                    updates.append({'name': parts[0], 'id': parts[1], 'current_ver': parts[2], 'new_ver': parts[3]})
            self.finished.emit(updates)
        except Exception as e:
            self.error.emit(str(e))

# --- 2. WORKER PRO AKTUALIZACI ---
class UpdateWorker(QThread):
    log_signal = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, app_id=None, update_all=False):
        super().__init__()
        self.app_id = app_id
        self.update_all = update_all

    def run(self):
        cmd = "winget upgrade --all --include-unknown --accept-package-agreements --accept-source-agreements" if self.update_all else \
              f'winget upgrade --id "{self.app_id}" --include-unknown --accept-package-agreements --accept-source-agreements'
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True, text=True, encoding='utf-8', errors='replace', startupinfo=startupinfo)
            for line in process.stdout:
                self.log_signal.emit(line.strip())
            process.wait()
            self.log_signal.emit("\nHotovo.")
        except Exception as e:
            self.log_signal.emit(f"\nChyba: {str(e)}")
        self.finished.emit()

# --- 3. WIDGET PRO ŘÁDEK AKTUALIZACE (BEZ IKONEK) ---
class UpdateRowWidget(QWidget):
    def __init__(self, data, parent_view):
        super().__init__()
        self.data = data
        self.parent_view = parent_view
        layout = QHBoxLayout(self)
        layout.setContentsMargins(25, 12, 25, 12)
        layout.setSpacing(0)
        
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        name_lbl = QLabel(data['name'])
        name_lbl.setStyleSheet("font-weight: bold; font-size: 14px; color: white; background: transparent;")
        ver_lbl = QLabel(f"{data['current_ver']}  ➜  {data['new_ver']}")
        ver_lbl.setStyleSheet(f"color: {COLORS['accent']}; font-size: 12px; background: transparent;")
        info_layout.addWidget(name_lbl)
        info_layout.addWidget(ver_lbl)
        layout.addLayout(info_layout)
        layout.addStretch()
        
        btn_update = QPushButton("Aktualizovat")
        btn_update.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_update.setFixedSize(110, 32)
        btn_update.setStyleSheet(f"""
            QPushButton {{ 
                background-color: rgba(255, 255, 255, 0.05); 
                color: {COLORS['accent']}; 
                border: 1px solid {COLORS['border']}; 
                border-radius: 6px; 
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{ 
                background-color: {COLORS['accent']}; 
                color: white; 
                border: 1px solid {COLORS['accent']};
            }}
        """)
        btn_update.clicked.connect(lambda: self.parent_view.run_update(self.data['id'], self.data['name']))
        layout.addWidget(btn_update)

# --- 4. HLAVNÍ UI (UpdaterPage) ---
class UpdaterPage(QWidget):
    def __init__(self):
        super().__init__()
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setSpacing(20)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        lbl_title = QLabel("Aktualizace aplikací")
        lbl_title.setStyleSheet("font-size: 24px; font-weight: bold; color: white;")
        lbl_sub = QLabel("Skenování a správa verzí softwaru")
        lbl_sub.setStyleSheet(f"color: {COLORS['sub_text']}; font-size: 13px;")
        title_box.addWidget(lbl_title)
        title_box.addWidget(lbl_sub)
        header.addLayout(title_box)
        header.addStretch()

        self.btn_refresh = QPushButton("Skenovat dostupné aktualizace")
        self._style_btn(self.btn_refresh, COLORS['input_bg'], "white")
        self.btn_refresh.clicked.connect(self.scan_updates)
        header.addWidget(self.btn_refresh)
        
        self.btn_update_all = QPushButton("Aktualizovat vše")
        self._style_btn(self.btn_update_all, COLORS['accent'], "white")
        self.btn_update_all.clicked.connect(self.run_update_all)
        self.btn_update_all.setEnabled(False)
        header.addWidget(self.btn_update_all)
        main_layout.addLayout(header)

        # SEZNAM S VIDITELNÝM MODERNÍM SLIDEREM
        self.list_widget = QListWidget()
        self.list_widget.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.list_widget.setStyleSheet(self._get_scroll_style())
        main_layout.addWidget(self.list_widget, stretch=3)

        self.progress = QProgressBar()
        self.progress.setStyleSheet(f"QProgressBar {{ min-height: 2px; max-height: 2px; background: transparent; border: none; }} QProgressBar::chunk {{ background-color: {COLORS['accent']}; }}")
        self.progress.setTextVisible(False)
        self.progress.setRange(0, 0)
        self.progress.hide()
        main_layout.addWidget(self.progress)

        # LOG KONZOLE S MODERNÍM SLIDEREM
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setPlaceholderText("Průběh aktualizace se zobrazí zde...")
        self.console.setStyleSheet(self._get_scroll_style(is_console=True))
        main_layout.addWidget(self.console, stretch=1)

    def _get_scroll_style(self, is_console=False):
        bg = "rgba(0, 0, 0, 0.2)" if is_console else COLORS['bg_sidebar']
        radius = "8px"
        padding = "10px" if is_console else "0px"
        return f"""
            { 'QTextEdit' if is_console else 'QListWidget' } {{ 
                background-color: {bg}; 
                border: 1px solid {COLORS['border']}; 
                border-radius: {radius}; 
                outline: none;
                padding: {padding};
                color: { '#888' if is_console else 'white' };
                font-family: { "'Consolas', monospace" if is_console else "'Segoe UI'" };
                font-size: { "11px" if is_console else "14px" };
            }}
            QScrollBar:vertical {{
                border: none;
                background: rgba(0,0,0,0.1);
                width: 8px;
                margin: 2px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: #444;
                border-radius: 4px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {COLORS['accent']};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical, QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                height: 0px; background: none;
            }}
        """

    def _style_btn(self, btn, bg, fg):
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(36)
        btn.setStyleSheet(f"QPushButton {{ background-color: {bg}; color: {fg}; border: none; padding: 0px 20px; border-radius: 6px; font-weight: bold; font-size: 13px; }} QPushButton:hover {{ background-color: {COLORS['accent_hover'] if bg == COLORS['accent'] else '#333'}; }} QPushButton:disabled {{ background-color: #222; color: #555; }}")

    def scan_updates(self):
        self.list_widget.clear()
        self.console.clear()
        self.btn_refresh.setEnabled(False)
        self.btn_update_all.setEnabled(False)
        self.progress.show()
        self.console.append("Hledám aktualizace...")
        self.scan_worker = ScanWorker()
        self.scan_worker.finished.connect(self.on_scan_finished)
        self.scan_worker.error.connect(lambda e: self.console.append(f"Chyba: {e}"))
        self.scan_worker.start()

    def on_scan_finished(self, updates):
        self.progress.hide()
        self.btn_refresh.setEnabled(True)
        if not updates:
            self.console.append("Všechny aplikace jsou aktuální.")
            return
        self.btn_update_all.setEnabled(True)
        self.btn_update_all.setText(f"Aktualizovat vše ({len(updates)})")
        for up in updates:
            item = QListWidgetItem(self.list_widget)
            item.setSizeHint(QSize(0, 65))
            self.list_widget.setItemWidget(item, UpdateRowWidget(up, self))

    def run_update(self, app_id, app_name):
        self._prepare_update_ui()
        self.console.append(f"Spouštím aktualizaci: {app_name}...")
        self.up_worker = UpdateWorker(app_id=app_id, update_all=False)
        self.up_worker.log_signal.connect(self.append_log)
        self.up_worker.finished.connect(self.on_update_finished)
        self.up_worker.start()

    def run_update_all(self):
        self._prepare_update_ui()
        self.console.append("Spouštím hromadnou aktualizaci...")
        self.up_worker = UpdateWorker(update_all=True)
        self.up_worker.log_signal.connect(self.append_log)
        self.up_worker.finished.connect(self.on_update_finished)
        self.up_worker.start()

    def _prepare_update_ui(self):
        self.progress.show()
        self.btn_refresh.setEnabled(False)
        self.btn_update_all.setEnabled(False)
        self.list_widget.setEnabled(False)

    def append_log(self, text):
        self.console.append(text)
        self.console.verticalScrollBar().setValue(self.console.verticalScrollBar().maximum())

    def on_update_finished(self):
        self.progress.hide()
        self.list_widget.setEnabled(True)
        self.btn_refresh.setEnabled(True)
        self.scan_updates()