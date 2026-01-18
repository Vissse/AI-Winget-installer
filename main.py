import sys
import os
import ctypes
from ctypes import windll, byref, c_int
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QListWidget, QListWidgetItem, QStackedWidget, QMessageBox, QLabel, 
                             QPushButton, QDialog, QTextEdit, QFrame)
from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QIcon

import styles
from config import COLORS

# Importy stránek
from view_home import HomePage
from view_specs import SpecsPage  # <--- NOVÝ IMPORT
from view_uninstaller import UninstallerPage
from view_installer import InstallerPage
from view_settings import SettingsPage
from view_health import HealthCheckPage
from view_updater import UpdaterPage
from splash import SplashScreen
import boot_system
from updater import AppUpdater

def resource_path(relative_path):
    try:
        if getattr(sys, 'frozen', False):
            base_path = os.path.dirname(sys.executable)
        else:
            base_path = os.path.abspath(".")
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# (HelpDialog může zůstat stejný, nebo ho zkopírujte z minula)
class HelpDialog(QDialog):
    pass 

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Univerzální aplikace")
        self.resize(1150, 750)
        
        icon_path = resource_path("program_icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        self.apply_custom_title_bar()

        try:
            self.setStyleSheet(styles.get_stylesheet())
        except Exception: pass

        self.updater = AppUpdater(self)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # === LEVÝ PANEL (SIDEBAR) ===
        sidebar_container = QWidget()
        sidebar_container.setFixedWidth(260)
        sidebar_container.setStyleSheet(f"background-color: {COLORS['bg_sidebar']}; border-right: 1px solid {COLORS['border']};")
        sidebar_layout = QVBoxLayout(sidebar_container)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        self.sidebar_list = QListWidget()
        self.sidebar_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.sidebar_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.sidebar_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.sidebar_list.setMouseTracking(True)
        def on_list_mouse_move(event):
            item = self.sidebar_list.itemAt(event.position().toPoint())
            if item and item.data(Qt.ItemDataRole.UserRole) is not None:
                self.sidebar_list.setCursor(Qt.CursorShape.PointingHandCursor)
            else:
                self.sidebar_list.setCursor(Qt.CursorShape.ArrowCursor)
            QListWidget.mouseMoveEvent(self.sidebar_list, event)
        self.sidebar_list.mouseMoveEvent = on_list_mouse_move
        
        self.sidebar_list.setStyleSheet(f"""
            QListWidget {{ background-color: transparent; border: none; outline: none; margin-top: 15px; }}
            QListWidget::item {{ 
                padding: 12px 10px;
                margin: 2px 10px; 
                border-radius: 6px; 
                color: {COLORS['sub_text']}; 
                font-weight: 500; 
            }}
            QListWidget::item:selected {{ 
                background-color: {COLORS['item_bg']}; 
                color: {COLORS['fg']}; 
                border-left: 3px solid {COLORS['accent']}; 
            }}
            QListWidget::item:hover {{ 
                background-color: {COLORS['item_hover']}; 
                color: {COLORS['fg']}; 
            }}
        """)
        
        self.sidebar_list.itemClicked.connect(self.on_sidebar_click)
        
        # --- DEFINICE STRÁNEK V MENU ---
        # Pořadí v menu (vizuální):
        
        # 1. SEKCE: PŘEHLED
        self.add_sidebar_item("🏠  Přehled", target_index=0)
        self.add_sidebar_separator()
        
        # 2. SEKCE: APLIKACE (Instalace, Update, Uninstall)
        self.add_sidebar_item("📦  Chytrá instalace", target_index=1)
        self.add_sidebar_item("🔄  Aktualizace aplikací", target_index=2)
        self.add_sidebar_item("🗑️  Odinstalace aplikací", target_index=4) # Pozor: Index 4 ve stacku
        self.add_sidebar_separator()
        
        # 3. SEKCE: SYSTÉM (Zdraví, Specifikace)
        self.add_sidebar_item("🩺  Kontrola stavu PC", target_index=3) # Pozor: Index 3 ve stacku
        self.add_sidebar_item("🖥️  Specifikace PC", target_index=6)    # Nová stránka (Index 6)
        
        sidebar_layout.addWidget(self.sidebar_list)

        # Spodní část (Nastavení)
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background-color: {COLORS['border']}; margin: 5px 15px;")
        sidebar_layout.addWidget(sep)

        bottom_buttons_layout = QHBoxLayout()
        bottom_buttons_layout.setContentsMargins(15, 0, 15, 20)
        bottom_buttons_layout.setSpacing(10)

        self.btn_settings = QPushButton("⚙️ Nastavení")
        self.btn_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_settings.setFixedHeight(40)
        self.btn_settings.clicked.connect(self.go_to_settings)
        self._style_bottom_btn(self.btn_settings)

        bottom_buttons_layout.addWidget(self.btn_settings, stretch=1)
        sidebar_layout.addLayout(bottom_buttons_layout)
        main_layout.addWidget(sidebar_container)

        # === HLAVNÍ OBSAH (STACK) ===
        self.pages = QStackedWidget()
        main_layout.addWidget(self.pages)
        
        self.home_page = HomePage()
        self.specs_page = SpecsPage() # Nová instance
        
        # INDEXY VE STACKU (MUSÍ SEDĚT S TARGET_INDEX V MENU):
        self.pages.addWidget(self.home_page)            # Index 0
        self.pages.addWidget(InstallerPage())           # Index 1
        self.pages.addWidget(UpdaterPage())             # Index 2
        self.pages.addWidget(HealthCheckPage())         # Index 3
        try: self.pages.addWidget(UninstallerPage())    # Index 4
        except: self.pages.addWidget(QLabel("Chyba"))
        self.pages.addWidget(SettingsPage(updater=self.updater)) # Index 5 (Nastavení)
        self.pages.addWidget(self.specs_page)           # Index 6 (Specifikace)
        
        # Start
        self.navigate_to_page(0)

    # --- METODY ---

    def add_sidebar_item(self, text, target_index):
        item = QListWidgetItem(text)
        item.setData(Qt.ItemDataRole.UserRole, target_index)
        self.sidebar_list.addItem(item)

    def add_sidebar_separator(self):
        item = QListWidgetItem("")
        item.setFlags(Qt.ItemFlag.NoItemFlags)
        item.setSizeHint(QSize(0, 20))
        self.sidebar_list.addItem(item)
        
        line_frame = QFrame()
        line_frame.setFrameShape(QFrame.Shape.HLine)
        line_frame.setStyleSheet(f"background-color: {COLORS['border']}; border: none; min-height: 1px; max-height: 1px; margin: 9px 15px;")
        self.sidebar_list.setItemWidget(item, line_frame)

    def on_sidebar_click(self, item):
        target_index = item.data(Qt.ItemDataRole.UserRole)
        if target_index is not None:
            self.switch_main_page(target_index)

    def navigate_to_page(self, index):
        for i in range(self.sidebar_list.count()):
            item = self.sidebar_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == index:
                self.sidebar_list.setCurrentRow(i)
                break
        self.switch_main_page(index)

    def switch_main_page(self, index):
        if index >= 0:
            self.pages.setCurrentIndex(index)
            self._style_bottom_btn(self.btn_settings, active=False)

    def go_to_settings(self):
        self.sidebar_list.clearSelection()
        self.switch_main_page(5)
        self._style_bottom_btn(self.btn_settings, active=True)

    def _style_bottom_btn(self, btn, active=False):
        bg_color = COLORS['item_bg'] if active else "transparent"
        border = f"1px solid {COLORS['accent']}" if active else "none"
        text_color = "white" if active else COLORS['sub_text']
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_color}; color: {text_color}; border: {border};
                border-radius: 6px; font-weight: bold; text-align: center;
            }}
            QPushButton:hover {{ background-color: {COLORS['item_hover']}; color: white; }}
        """)

    def apply_custom_title_bar(self):
        try:
            hwnd = self.winId().__int__() 
            windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, byref(c_int(1)), 4)
            hex_color = COLORS['bg_sidebar']
            r, g, b = int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)
            windll.dwmapi.DwmSetWindowAttribute(hwnd, 35, byref(c_int(b << 16 | g << 8 | r)), 4)
            windll.dwmapi.DwmSetWindowAttribute(hwnd, 36, byref(c_int(255 << 16 | 255 << 8 | 255)), 4)
        except: pass

if __name__ == "__main__":
    boot_system.perform_boot_checks()
    try:
        myappid = 'mycompany.winget.installer.v8' 
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception: pass

    app = QApplication(sys.argv)
    app.aboutToQuit.connect(lambda: os._exit(0))
    splash = SplashScreen()
    splash.show()
    def start_program():
        global window
        window = MainWindow()
        window.show()
    splash.finished.connect(start_program)
    app.exec()