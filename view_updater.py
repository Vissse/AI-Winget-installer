import subprocess
import re
import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QListWidget, QListWidgetItem, 
                             QProgressBar, QFrame, QLineEdit, QFileIconProvider)
from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal, QFileInfo
from PyQt6.QtGui import QIcon
from config import COLORS
from view_installer import HoverButton, IconWorker
from config import resource_path

# --- 1. WORKERY (Zůstávají stejné) ---
class ScanWorker(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    
    def run(self):
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            cmd = "winget upgrade --include-unknown --accept-source-agreements"
            res = subprocess.run(cmd, capture_output=True, text=True, startupinfo=startupinfo, encoding='utf-8', errors='replace')
            updates = []
            parsing = False
            for line in res.stdout.split('\n'):
                if "Name" in line and "Id" in line: 
                    parsing = True
                    continue
                if not parsing or "----" in line or not line.strip(): 
                    continue
                p = re.split(r'\s{2,}', line.strip())
                if len(p) >= 4: 
                    updates.append({'name': p[0], 'id': p[1], 'current': p[2], 'new': p[3]})
            self.finished.emit(updates)
        except Exception as e: 
            self.error.emit(str(e))

class UpdateWorker(QThread):
    finished = pyqtSignal()
    def __init__(self, app_id=None, update_all=False):
        super().__init__()
        self.app_id = app_id
        self.update_all = update_all

    def run(self):
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        cmd = "winget upgrade --all --include-unknown --accept-package-agreements --accept-source-agreements" if self.update_all else f"winget upgrade --id {self.app_id} --exact --accept-package-agreements --accept-source-agreements"
        subprocess.run(cmd, shell=False, startupinfo=startupinfo)
        self.finished.emit()

# --- 2. UI KOMPONENTY ---
class UpdateRowWidget(QWidget):
    def __init__(self, data, parent_page):
        super().__init__()
        self.data = data
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(15)

        # 1. Ikona (Offline systémová)
        self.icon_lbl = QLabel()
        self.icon_lbl.setFixedSize(24, 24)
        
        # Získání systémové ikony
        self.set_offline_icon(data['name'], data['id'])
        
        layout.addWidget(self.icon_lbl)

        # 2. Název (Dynamický stretch)
        name_lbl = QLabel(data['name'])
        name_lbl.setStyleSheet("font-weight: bold; color: white;")
        name_lbl.setWordWrap(False) # Zabráníme roztažení řádku do výšky
        layout.addWidget(name_lbl, stretch=1)

        # 3. Stávající verze (FIXNÍ ŠÍŘKA 150px)
        curr_lbl = QLabel(data['current'])
        curr_lbl.setFixedWidth(150)
        curr_lbl.setStyleSheet(f"color: {COLORS['sub_text']};")
        layout.addWidget(curr_lbl)

        # 4. Dostupná verze (FIXNÍ ŠÍŘKA 150px)
        new_lbl = QLabel(data['new'])
        new_lbl.setFixedWidth(150)
        new_lbl.setStyleSheet(f"color: {COLORS['accent']}; font-weight: bold;")
        layout.addWidget(new_lbl)

        # 5. Akce (FIXNÍ ŠÍŘKA 110px)
        self.btn_up = QPushButton("Aktualizovat")
        self.btn_up.setFixedWidth(110)
        self.btn_up.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_up.setStyleSheet(f"QPushButton {{ background: transparent; color: {COLORS['accent']}; font-weight: bold; border: 1px solid {COLORS['accent']}; border-radius: 4px; padding: 4px; }} QPushButton:hover {{ background: {COLORS['accent']}; color: white; }}")
        self.btn_up.clicked.connect(lambda: self.parent_page.run_update(data['id'], data['name']))
        layout.addWidget(self.btn_up)

    def set_offline_icon(self, name, app_id):
        icon_provider = QFileIconProvider()
        
        # Zkusíme najít cestu k aplikaci (běžné lokace)
        search_paths = [
            f"C:\\Program Files\\{name}",
            f"C:\\Program Files (x86)\\{name}",
            f"C:\\Program Files\\{app_id.split('.')[0]}"
        ]
        
        found_icon = False
        for path in search_paths:
            if os.path.exists(path):
                icon = icon_provider.icon(QFileInfo(path))
                if not icon.isNull():
                    pixmap = icon.pixmap(24, 24)
                    self.icon_lbl.setPixmap(pixmap)
                    found_icon = True
                    break
        
        if not found_icon:
            # Fallback na systémovou ikonu "Aplikace" (.exe)
            self.icon_lbl.setText("📦")
            self.icon_lbl.setStyleSheet("font-size: 11pt; color: #555;")

class UpdaterPage(QWidget):
    scan_finished_signal = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.all_updates = [] # Cache pro vyhledávání
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # === A. HORNÍ VYHLEDÁVACÍ LIŠTA (Sjednoceno s Installerem) ===
        top_bar = QWidget()
        top_bar.setStyleSheet(f"background-color: {COLORS['bg_main']}; border-bottom: 1px solid {COLORS['border']};")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(20, 15, 20, 15)
        
        lbl_title = QLabel("Aktualizace")
        lbl_title.setStyleSheet("font-size: 14pt; font-weight: bold; color: white; border: none;")
        top_layout.addWidget(lbl_title)
        top_layout.addSpacing(20)

        # Vyhledávací kontejner
        self.search_container = QFrame()
        self.search_container.setFixedWidth(500)
        self.search_container.setFixedHeight(38)
        self.search_container.setStyleSheet(f"QFrame {{ background-color: {COLORS['input_bg']}; border: 1px solid {COLORS['border']}; border-radius: 6px; }} QFrame:focus-within {{ border: 1px solid {COLORS['accent']}; }}")
        search_cont_layout = QHBoxLayout(self.search_container)
        search_cont_layout.setContentsMargins(10, 0, 5, 0)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Hledat v aktualizacích...")
        self.search_input.setStyleSheet("border: none; background: transparent; color: white; font-size: 10pt;")
        self.search_input.textChanged.connect(self.filter_updates)
        
        self.btn_search_icon = HoverButton("", "images/magnifying-glass-thin.png", "fg")
        self.btn_search_icon.setFixedSize(32, 32)
        self.btn_search_icon.setIconSize(QSize(18, 18))

        search_cont_layout.addWidget(self.search_input)
        search_cont_layout.addWidget(self.btn_search_icon)
        top_layout.addWidget(self.search_container)
        
        top_layout.addStretch()
        main_layout.addWidget(top_bar)

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setFixedHeight(2)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet(f"QProgressBar {{ border: none; background: transparent; }} QProgressBar::chunk {{ background-color: {COLORS['accent']}; }}")
        self.progress.hide()
        main_layout.addWidget(self.progress)

        # === B. ACTION BAR ===
        action_bar = QWidget()
        action_bar.setStyleSheet(f"background-color: {COLORS['bg_main']};")
        action_layout = QHBoxLayout(action_bar)
        action_layout.setContentsMargins(20, 10, 20, 10)

        self.btn_refresh = QPushButton("  Skenovat")
        self.btn_refresh.setIcon(QIcon(resource_path("images/arrows-clockwise-thin.png")))
        self.btn_refresh.setFixedHeight(34)
        self.btn_refresh.setStyleSheet(f"QPushButton {{ background-color: {COLORS['item_bg']}; color: white; border: 1px solid {COLORS['border']}; padding: 0 15px; border-radius: 6px; font-weight: bold; }} QPushButton:hover {{ border-color: {COLORS['accent']}; }}")
        self.btn_refresh.clicked.connect(self.scan_updates)
        action_layout.addWidget(self.btn_refresh)
        
        self.btn_update_all = QPushButton("  Aktualizovat vše")
        self.btn_update_all.setFixedHeight(34)
        self.btn_update_all.setEnabled(False)
        self.btn_update_all.setStyleSheet(f"QPushButton {{ background-color: {COLORS['accent']}; color: white; border: none; padding: 0 15px; border-radius: 6px; font-weight: bold; }} QPushButton:disabled {{ background-color: #222; color: #555; }}")
        self.btn_update_all.clicked.connect(self.run_update_all)
        action_layout.addWidget(self.btn_update_all)
        
        action_layout.addStretch()
        self.status_lbl = QLabel("Připraveno")
        self.status_lbl.setStyleSheet(f"color: {COLORS['sub_text']};")
        action_layout.addWidget(self.status_lbl)
        main_layout.addWidget(action_bar)

        # === C. HLAVIČKA TABULKY (S FIXNÍMI ŠÍŘKAMI) ===
        header_widget = QWidget()
        header_widget.setStyleSheet(f"background-color: {COLORS['bg_sidebar']}; border: none; font-size: 9pt;")
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(35, 8, 35, 8) 
        header_layout.setSpacing(15)

        # Definice šířek (musí sedět s UpdateRowWidget)
        h_headers = [
            ("", 24, 0), 
            ("NÁZEV APLIKACE", 0, 1), 
            ("STÁVAJÍCÍ", 150, 0), 
            ("DOSTUPNÁ", 150, 0), 
            ("AKCE", 110, 0)
        ]
        
        for text, width, stretch in h_headers:
            lbl = QLabel(text)
            lbl.setStyleSheet("font-weight: bold; color: white;")
            if width > 0: lbl.setFixedWidth(width)
            header_layout.addWidget(lbl, stretch=stretch)
            
        main_layout.addWidget(header_widget)

        # === D. SEZNAM ===
        self.list_widget = QListWidget()
        self.list_widget.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.list_widget.setStyleSheet(f"QListWidget {{ background-color: {COLORS['bg_main']}; border: none; padding: 0 30px; }} QListWidget::item {{ border-bottom: 1px solid {COLORS['border']}; }} QListWidget::item:hover {{ background-color: {COLORS['item_hover']}; }}")
        # Minimalistický scroller
        self.list_widget.verticalScrollBar().setStyleSheet(f"QScrollBar:vertical {{ border: none; background: transparent; width: 4px; }} QScrollBar::handle:vertical {{ background: #333; border-radius: 2px; }} QScrollBar::handle:vertical:hover {{ background: {COLORS['accent']}; }}")
        main_layout.addWidget(self.list_widget)

    def scan_updates(self):
        self.list_widget.clear()
        self.all_updates = []
        self.btn_refresh.setEnabled(False)
        self.status_lbl.setText("Hledám aktualizace...")
        self.progress.setRange(0, 0)
        self.progress.show()
        
        self.scan_worker = ScanWorker()
        self.scan_worker.finished.connect(self.on_scan_finished)
        self.scan_worker.error.connect(lambda e: self.on_scan_finished([]))
        self.scan_worker.start()

    def on_scan_finished(self, updates):
        self.progress.hide()
        self.btn_refresh.setEnabled(True)
        self.all_updates = updates
        self.scan_finished_signal.emit(updates)
        self.render_list(updates)

    def render_list(self, updates):
        self.list_widget.clear()
        if updates: 
            self.btn_update_all.setEnabled(True)
            self.btn_update_all.setText(f"  Aktualizovat vše ({len(updates)})")
            self.status_lbl.setText(f"Nalezeno {len(updates)} aktualizací")
        else:
            self.btn_update_all.setEnabled(False)
            self.status_lbl.setText("Vše je aktuální")
            self.show_empty_message()
            
        for u in updates:
            item = QListWidgetItem(self.list_widget)
            item.setSizeHint(QSize(0, 50))
            self.list_widget.setItemWidget(item, UpdateRowWidget(u, self))

    def filter_updates(self, text):
        filtered = [u for u in self.all_updates if text.lower() in u['name'].lower() or text.lower() in u['id'].lower()]
        self.render_list(filtered)

    def show_empty_message(self):
        item = QListWidgetItem(self.list_widget)
        lbl = QLabel("Všechny aplikace jsou aktuální ✨")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet("color: #666; padding: 40px; font-size: 10pt;")
        item.setSizeHint(QSize(0, 120))
        self.list_widget.setItemWidget(item, lbl)

    def run_update(self, aid, name):
        self.status_lbl.setText(f"Aktualizuji {name}...")
        self.up_worker = UpdateWorker(app_id=aid)
        self.up_worker.finished.connect(self.scan_updates)
        self.up_worker.start()

    def run_update_all(self):
        self.status_lbl.setText("Aktualizuji vše...")
        self.up_worker = UpdateWorker(update_all=True)
        self.up_worker.finished.connect(self.scan_updates)
        self.up_worker.start()