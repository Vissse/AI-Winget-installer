import winreg
import os
import requests
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QListWidget, QListWidgetItem, QLineEdit, 
                             QMessageBox, QFileIconProvider, QFrame, QProgressBar)
from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal, QFileInfo
from PyQt6.QtGui import QPixmap, QImage, QIcon

from workers import WingetListWorker, UninstallWorker
from config import COLORS
from view_installer import HoverButton
from config import resource_path

# --- 1. WORKER PRO IKONY ---
class LocalIconWorker(QThread):
    loaded = pyqtSignal(QPixmap)

    def __init__(self, app_id, app_name, known_paths=None):
        super().__init__()
        self.app_id = app_id
        self.app_name = app_name
        self.known_paths = known_paths or {}

    def run(self):
        if self.app_id in self.known_paths:
            pixmap = self.extract_local_icon(self.known_paths[self.app_id])
            if pixmap:
                self.loaded.emit(pixmap)
                return
        self.try_online_search()

    def extract_local_icon(self, path):
        try:
            clean_path = path.split(',')[0].strip().replace('"', '')
            if os.path.exists(clean_path):
                icon = QFileIconProvider().icon(QFileInfo(clean_path))
                if not icon.isNull(): return icon.pixmap(32, 32)
        except: pass
        return None

    def try_online_search(self):
        clean_id = self.app_id
        urls = [
            f"https://cdn.jsdelivr.net/gh/walkxcode/dashboard-icons/png/{clean_id.lower().replace('.', '-')}.png",
            f"https://raw.githubusercontent.com/marticliment/UnigetUI/main/src/UnigetUI.PackageEngine/Assets/Packages/{clean_id}.png"
        ]
        for url in urls:
            try:
                r = requests.get(url, timeout=1.5)
                if r.status_code == 200:
                    img = QImage(); img.loadFromData(r.content)
                    if not img.isNull():
                        pix = QPixmap.fromImage(img).scaled(24, 24, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                        self.loaded.emit(pix); return
            except: continue

# --- 2. SKENOVÁNÍ REGISTRŮ ---
def scan_registry_for_icons():
    apps_icons = {}
    reg_paths = [r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall", r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"]
    for root in [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]:
        for p in reg_paths:
            try:
                key = winreg.OpenKey(root, p)
                for i in range(winreg.QueryInfoKey(key)[0]):
                    try:
                        name = winreg.EnumKey(key, i)
                        with winreg.OpenKey(key, name) as sub:
                            disp = winreg.QueryValueEx(sub, "DisplayName")[0]
                            try: icon = winreg.QueryValueEx(sub, "DisplayIcon")[0]
                            except: icon = None
                            if disp and icon: apps_icons[disp.lower()] = icon; apps_icons[name.lower()] = icon
                    except: continue
            except: continue
    return apps_icons

# --- 3. WIDGET ŘÁDKU ---
class AppItemWidget(QWidget):
    def __init__(self, name, app_id, parent_view, known_paths):
        super().__init__()
        self.app_id = app_id
        self.parent_view = parent_view
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5) # Sladěno s hlavičkou
        layout.setSpacing(15)

        self.icon_lbl = QLabel()
        self.icon_lbl.setFixedSize(24, 24)
        self.icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_lbl.setText("📦")
        self.icon_lbl.setStyleSheet("font-size: 12pt; color: #888; background: transparent;")
        layout.addWidget(self.icon_lbl)

        self.icon_worker = LocalIconWorker(app_id, name, {app_id: known_paths.get(app_id.lower()) or known_paths.get(name.lower())})
        self.icon_worker.loaded.connect(self.set_icon); self.icon_worker.start()

        self.name_lbl = QLabel(name)
        self.name_lbl.setStyleSheet("font-weight: bold; color: white; background: transparent;")
        layout.addWidget(self.name_lbl, stretch=1)

        # Kontejner pro tlačítko se stejnou šířkou jako má nadpis v hlavičce
        self.btn_un = QPushButton("Odinstalovat")
        self.btn_un.setFixedWidth(130) 
        self.btn_un.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_un.setStyleSheet(f"""
            QPushButton {{ 
                background: transparent; 
                color: {COLORS['sub_text']}; 
                font-weight: bold; 
                border: none; 
                text-align: left;
                padding-right: 0px;
            }} 
            QPushButton:hover {{ 
                color: {COLORS['accent']}; 
            }}
        """)
        self.btn_un.clicked.connect(lambda: self.parent_view.confirm_uninstall(self.app_id))
        layout.addWidget(self.btn_un)

    def set_icon(self, pix):
        self.icon_lbl.setPixmap(pix); self.icon_lbl.setText("")

# --- 4. STRÁNKA ---
class UninstallerPage(QWidget):
    def __init__(self):
        super().__init__()
        self.registry_cache = {}; self.all_items = []
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0); main_layout.setSpacing(0)

        # HORNÍ LIŠTA
        top_bar = QWidget()
        top_bar.setStyleSheet(f"background-color: {COLORS['bg_main']}; border-bottom: 1px solid {COLORS['border']};")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(20, 15, 20, 15)

        lbl_title = QLabel("Odinstalace")
        lbl_title.setStyleSheet("font-size: 14pt; font-weight: bold; color: white; border: none;")
        top_layout.addWidget(lbl_title)
        top_layout.addSpacing(20)

        self.search_container = QFrame()
        self.search_container.setFixedWidth(700); self.search_container.setFixedHeight(38)
        self.search_container.setStyleSheet(f"QFrame {{ background-color: {COLORS['input_bg']}; border: 1px solid {COLORS['border']}; border-radius: 6px; }} QFrame:focus-within {{ border: 1px solid {COLORS['accent']}; }}")
        s_layout = QHBoxLayout(self.search_container)
        s_layout.setContentsMargins(10, 0, 5, 0)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Hledat v nainstalovaných aplikacích...")
        self.search_input.setStyleSheet("border: none; background: transparent; color: white; font-size: 10pt;")
        self.search_input.textChanged.connect(self.filter_items)

        self.btn_search_icon = HoverButton("", "images/magnifying-glass-thin.png", "fg")
        self.btn_search_icon.setFixedSize(32, 32); self.btn_search_icon.setIconSize(QSize(18, 18))
        self.btn_search_icon.setStyleSheet("background: transparent; border: none;")

        s_layout.addWidget(self.search_input); s_layout.addWidget(self.btn_search_icon)
        top_layout.addWidget(self.search_container); top_layout.addStretch()
        main_layout.addWidget(top_bar)

        # === PROGRESS BAR (přidáno) ===
        self.progress = QProgressBar()
        self.progress.setFixedHeight(2)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet(f"QProgressBar {{ border: none; background: transparent; }} QProgressBar::chunk {{ background-color: {COLORS['accent']}; }}")
        self.progress.hide()
        main_layout.addWidget(self.progress)

        # ACTION BAR
        action_bar = QWidget()
        action_bar.setStyleSheet(f"background-color: {COLORS['bg_main']};")
        action_layout = QHBoxLayout(action_bar)
        action_layout.setContentsMargins(20, 10, 20, 10)

        self.refresh_btn = QPushButton("  Načíst aplikace")
        self.refresh_btn.setIcon(QIcon(resource_path("images/arrows-clockwise-thin.png")))
        self.refresh_btn.setFixedHeight(34); self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.setStyleSheet(f"QPushButton {{ background-color: {COLORS['item_bg']}; color: white; border: 1px solid {COLORS['border']}; padding: 0 15px; border-radius: 6px; font-weight: bold; }} QPushButton:hover {{ border-color: {COLORS['accent']}; }}")
        self.refresh_btn.clicked.connect(self.load_apps)
        action_layout.addWidget(self.refresh_btn)
        
        action_layout.addStretch()
        self.status = QLabel("Připraveno."); self.status.setStyleSheet(f"color: {COLORS['sub_text']};")
        action_layout.addWidget(self.status)
        main_layout.addWidget(action_bar)

        # HLAVIČKA - Sjednoceno s řádkem
        header_widget = QWidget()
        header_widget.setStyleSheet(f"background-color: {COLORS['bg_sidebar']}; border: none; font-size: 9pt;")
        h_layout = QHBoxLayout(header_widget)
        h_layout.setContentsMargins(35, 8, 35, 8) # Identické s InstallerPage
        h_layout.setSpacing(15)
        
        h_headers = [("", 24), ("NÁZEV APLIKACE", 0), ("AKCE", 130)]
        for i, (text, width) in enumerate(h_headers):
            lbl = QLabel(text); lbl.setStyleSheet("font-weight: bold; color: white;")
            if width > 0: lbl.setFixedWidth(width)
            if i == 2: lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            h_layout.addWidget(lbl, stretch=(1 if i == 1 else 0))
        main_layout.addWidget(header_widget)

        # SEZNAM S MINIMALISTICKÝM SCROLLEREM
        self.list_widget = QListWidget()
        self.list_widget.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.list_widget.setStyleSheet(f"""
            QListWidget {{ 
                background-color: {COLORS['bg_main']}; 
                border: none; 
                outline: none; 
                padding: 0 30px; 
            }} 
            QListWidget::item {{ 
                border-bottom: 1px solid {COLORS['border']}; 
            }} 
            QListWidget::item:hover {{ 
                background-color: {COLORS['item_hover']}; 
            }}
            
            QScrollBar:vertical {{
                border: none;
                background: transparent;
                width: 4px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: #333;
                min-height: 20px;
                border-radius: 2px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {COLORS['accent']};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical, 
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                height: 0px; background: none;
            }}
        """)
        main_layout.addWidget(self.list_widget)

    def load_apps(self):
        self.list_widget.clear(); self.all_items = []
        self.refresh_btn.setEnabled(False); self.status.setText("Skenuji systém...")
        self.progress.setRange(0, 0); self.progress.show()
        try: self.registry_cache = scan_registry_for_icons()
        except: self.registry_cache = {}
        self.worker = WingetListWorker()
        self.worker.finished.connect(self.on_loaded)
        self.worker.error.connect(lambda e: self.status.setText(f"Chyba: {e}"))
        self.worker.start()

    def on_loaded(self, apps):
        self.progress.hide()
        for app in apps:
            item = QListWidgetItem(self.list_widget); item.setSizeHint(QSize(0, 50))
            widget = AppItemWidget(app['name'], app['id'], self, self.registry_cache)
            self.list_widget.setItemWidget(item, widget)
            self.all_items.append((item, widget, app['name'].lower()))
        self.refresh_btn.setEnabled(True); self.status.setText(f"Nalezeno {len(apps)} aplikací.")

    def filter_items(self, text):
        t = text.lower()
        for item, widget, name in self.all_items: 
            item.setHidden(t not in name and t not in widget.app_id.lower())

    def confirm_uninstall(self, app_id):
        if QMessageBox.question(self, "Odinstalovat", f"Opravdu odinstalovat aplikaci?\nID: {app_id}") == QMessageBox.StandardButton.Yes:
            self.status.setText("Odinstalovávám..."); self.u_worker = UninstallWorker(app_id)
            self.u_worker.finished.connect(self.load_apps); self.u_worker.start()