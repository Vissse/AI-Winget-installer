import subprocess
import re
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QListWidget, QListWidgetItem, 
                             QProgressBar, QMessageBox, QTextEdit, QSplitter)
from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal
from PyQt6.QtGui import QColor

from config import COLORS

# --- 1. WORKER PRO SKENOVÁNÍ (Hledání aktualizací) ---
class ScanWorker(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def run(self):
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            # Příkaz pro výpis aktualizací
            cmd = "winget upgrade --include-unknown --accept-source-agreements"
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                startupinfo=startupinfo, 
                encoding='utf-8', 
                errors='replace'
            )
            
            lines = result.stdout.split('\n')
            updates = []
            start_parsing = False
            
            # Jednoduchý parser tabulky, kterou vrací winget
            for line in lines:
                if line.startswith("Name") and "Id" in line:
                    start_parsing = True
                    continue
                if not start_parsing or "----" in line or not line.strip(): 
                    continue
                
                # Rozdělení podle více mezer (winget formátování)
                parts = re.split(r'\s{2,}', line.strip())
                
                # Očekáváme: Name, Id, Version, Available, Source
                if len(parts) >= 4:
                    updates.append({
                        'name': parts[0],
                        'id': parts[1],
                        'current_ver': parts[2],
                        'new_ver': parts[3]
                    })
            
            self.finished.emit(updates)

        except Exception as e:
            self.error.emit(str(e))

# --- 2. WORKER PRO AKTUALIZACI (Provádění změn) ---
class UpdateWorker(QThread):
    log_signal = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, app_id=None, update_all=False):
        super().__init__()
        self.app_id = app_id
        self.update_all = update_all

    def run(self):
        if self.update_all:
            self.log_signal.emit("--- ZAHAJUJI HROMADNOU AKTUALIZACI ---\n")
            cmd = "winget upgrade --all --include-unknown --accept-package-agreements --accept-source-agreements"
        else:
            self.log_signal.emit(f"--- AKTUALIZUJI: {self.app_id} ---\n")
            cmd = f'winget upgrade --id "{self.app_id}" --include-unknown --accept-package-agreements --accept-source-agreements'

        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT, 
                shell=True, 
                text=True, 
                encoding='utf-8', 
                errors='replace',
                startupinfo=startupinfo
            )

            # Čtení výstupu v reálném čase
            for line in process.stdout:
                self.log_signal.emit(line.strip())
            
            process.wait()
            self.log_signal.emit("\n✅ Hotovo.")
            
        except Exception as e:
            self.log_signal.emit(f"\n❌ Chyba: {str(e)}")
        
        self.finished.emit()

# --- 3. WIDGET PRO ŘÁDEK AKTUALIZACE ---
class UpdateRowWidget(QWidget):
    def __init__(self, data, parent_view):
        super().__init__()
        self.data = data
        self.parent_view = parent_view
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        
        # Ikona / Status
        lbl_icon = QLabel("🔄")
        lbl_icon.setStyleSheet("font-size: 16px; color: #888;")
        layout.addWidget(lbl_icon)

        # Info
        info_layout = QVBoxLayout()
        name_lbl = QLabel(data['name'])
        name_lbl.setStyleSheet("font-weight: bold; font-size: 14px; color: white;")
        
        ver_lbl = QLabel(f"{data['current_ver']}  ➜  {data['new_ver']}")
        ver_lbl.setStyleSheet(f"color: {COLORS['accent']}; font-weight: bold; font-size: 12px;")
        
        id_lbl = QLabel(data['id'])
        id_lbl.setStyleSheet(f"color: {COLORS['sub_text']}; font-size: 10px;")
        
        info_layout.addWidget(name_lbl)
        info_layout.addWidget(ver_lbl)
        info_layout.addWidget(id_lbl)
        layout.addLayout(info_layout)
        
        layout.addStretch()
        
        # Tlačítko Update
        btn_update = QPushButton("Update")
        btn_update.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_update.setStyleSheet(f"""
            QPushButton {{ 
                background-color: {COLORS['input_bg']}; color: {COLORS['success']}; 
                border: 1px solid {COLORS['border']}; border-radius: 4px; padding: 5px 15px; font-weight: bold;
            }}
            QPushButton:hover {{ 
                background-color: {COLORS['success']}; color: white; border: 1px solid {COLORS['success']};
            }}
        """)
        btn_update.clicked.connect(self.start_single_update)
        layout.addWidget(btn_update)

    def start_single_update(self):
        self.parent_view.run_update(app_id=self.data['id'], app_name=self.data['name'])


# --- 4. HLAVNÍ UI (UpdaterPage) ---
class UpdaterPage(QWidget):
    def __init__(self):
        super().__init__()
        
        # Rozdělení na Seznam (Nahoře) a Log (Dole)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(10)

        # --- HLAVIČKA ---
        header = QHBoxLayout()
        
        title_box = QVBoxLayout()
        lbl_title = QLabel("Aktualizace aplikací")
        lbl_title.setStyleSheet("font-size: 24px; font-weight: bold; color: white;")
        lbl_sub = QLabel("Správa aktualizací aplikací")
        lbl_sub.setStyleSheet(f"color: {COLORS['sub_text']};")
        title_box.addWidget(lbl_title)
        title_box.addWidget(lbl_sub)
        header.addLayout(title_box)
        
        header.addStretch()

        self.btn_refresh = QPushButton("⟳ Zkontrolovat aktualizace")
        self._style_btn(self.btn_refresh, COLORS['input_bg'], "white")
        self.btn_refresh.clicked.connect(self.scan_updates)
        header.addWidget(self.btn_refresh)
        
        self.btn_update_all = QPushButton("Aktualizovat vše")
        self._style_btn(self.btn_update_all, COLORS['accent'], "white")
        self.btn_update_all.clicked.connect(self.run_update_all)
        self.btn_update_all.setEnabled(False) # Deaktivováno, dokud nenajdeme updaty
        header.addWidget(self.btn_update_all)

        main_layout.addLayout(header)

        # --- SEZNAM ---
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(f"""
            QListWidget {{ background-color: {COLORS['bg_sidebar']}; border: none; border-radius: 6px; }}
            QListWidget::item {{ padding: 5px; }}
        """)
        self.list_widget.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        main_layout.addWidget(self.list_widget, stretch=2)

        # --- PROGRESS BAR ---
        self.progress = QProgressBar()
        self.progress.setStyleSheet(f"""
                QProgressBar {{ min-height: 4px; max-height: 4px; background: transparent; border: none; margin-top: 5px; }} 
                QProgressBar::chunk {{ background-color: {COLORS['accent']}; }}
            """)
        self.progress.setTextVisible(False)
        self.progress.setRange(0, 0)
        self.progress.hide()
        main_layout.addWidget(self.progress)

        # --- LOG KONZOLE (Skrytá defaultně, nebo malá) ---
        lbl_log = QLabel("Průběh aktualizace:")
        lbl_log.setStyleSheet(f"color: {COLORS['sub_text']}; font-weight: bold; margin-top: 10px;")
        main_layout.addWidget(lbl_log)

        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setStyleSheet(f"""
            QTextEdit {{
                background-color: #111; color: #ddd; font-family: Consolas; 
                border: 1px solid {COLORS['border']}; border-radius: 4px; font-size: 12px;
            }}
        """)
        main_layout.addWidget(self.console, stretch=1)

    def _style_btn(self, btn, bg, fg):
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{ 
                background-color: {bg}; color: {fg}; border: none; 
                padding: 8px 15px; border-radius: 4px; font-weight: bold; font-size: 13px;
            }}
            QPushButton:hover {{ background-color: {COLORS['accent_hover'] if bg == COLORS['accent'] else '#444'}; }}
            QPushButton:disabled {{ background-color: {COLORS['border']}; color: #888; }}
        """)

    # --- LOGIKA ---

    def scan_updates(self):
        self.list_widget.clear()
        self.console.clear()
        self.btn_refresh.setEnabled(False)
        self.btn_update_all.setEnabled(False)
        self.progress.show()
        
        self.console.append("Hledám aktualizace...")
        
        self.scan_worker = ScanWorker()
        self.scan_worker.finished.connect(self.on_scan_finished)
        self.scan_worker.error.connect(lambda e: self.console.append(f"Chyba skenu: {e}"))
        self.scan_worker.start()

    def on_scan_finished(self, updates):
        self.progress.hide()
        self.btn_refresh.setEnabled(True)
        
        if not updates:
            item = QListWidgetItem("Všechny aplikace jsou aktuální. 🎉")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.list_widget.addItem(item)
            self.console.append("Nebyly nalezeny žádné aktualizace.")
            return

        self.btn_update_all.setEnabled(True)
        self.btn_update_all.setText(f"Aktualizovat vše ({len(updates)})")
        self.console.append(f"Nalezeno {len(updates)} aktualizací.")

        for up in updates:
            item = QListWidgetItem(self.list_widget)
            item.setSizeHint(QSize(0, 70))
            widget = UpdateRowWidget(up, self)
            self.list_widget.setItemWidget(item, widget)

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
        self.list_widget.setEnabled(False) # Zablokovat list během updatu

    def append_log(self, text):
        self.console.append(text)
        # Autoscroll
        sb = self.console.verticalScrollBar()
        sb.setValue(sb.maximum())

    def on_update_finished(self):
        self.progress.hide()
        self.list_widget.setEnabled(True)
        self.btn_refresh.setEnabled(True)
        self.console.append("--- Operace dokončena ---")
        
        # Volitelně: Refresh seznamu po update
        self.scan_updates()