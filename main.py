import sys
import os
import ctypes
from ctypes import windll, byref, c_int
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QListWidget, QListWidgetItem, QStackedWidget, QMessageBox, QLabel, 
                             QPushButton, QDialog, QTextEdit, QFrame)
from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QIcon, QFont

import styles
from config import COLORS

# Importy stránek
from view_uninstaller import UninstallerPage
from view_installer import InstallerPage
from view_settings import SettingsPage
from view_health import HealthCheckPage
from view_updater import UpdaterPage
from splash import SplashScreen

def resource_path(relative_path):
    """ Získá absolutní cestu k souboru (funguje pro dev i pro PyInstaller exe) """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def is_admin():
    try: return ctypes.windll.shell32.IsUserAnAdmin()
    except: return False

# --- OKNO S NÁPOVĚDOU ---
class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Jak používat aplikaci")
        self.setFixedSize(600, 500)
        self.setStyleSheet(f"background-color: {COLORS['bg_main']}; color: {COLORS['fg']};")

        layout = QVBoxLayout(self)
        
        title = QLabel("📖 Průvodce aplikací")
        title.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {COLORS['accent']}; margin-bottom: 10px;")
        layout.addWidget(title)

        # Textové pole s vysvětlením
        text_area = QTextEdit()
        text_area.setReadOnly(True)
        text_area.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLORS['bg_sidebar']}; 
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
                color: #ddd;
            }}
        """)
        
        html_content = f"""
        <h3 style="color: {COLORS['accent']}">📦 Chytrá instalace aplikací</h3>
        <p>Umožňuje vyhledávat a hromadně instalovat aplikace pomocí AI a Winget. Můžete si vytvořit frontu a nainstalovat vše naraz.</p>
        
        <h3 style="color: {COLORS['accent']}">🔄 Aktualizace aplikací</h3>
        <p>Zkontroluje všechny nainstalované programy v PC a nabídne hromadnou aktualizaci na nejnovější verze.</p>
        
        <h3 style="color: {COLORS['accent']}">🩺 Kontrola stavu PC</h3>
        <p>Analyzuje zdraví systému (disk, baterie, RAM) a navrhne optimalizace (SFC scan, DISM).</p>
        
        <h3 style="color: {COLORS['accent']}">🗑️ Odinstalace aplikací</h3>
        <p>Čisté odstranění programů včetně zbytků, které běžný odinstalátor často nechává.</p>
        
        <hr>
        <p><i>Tip: V Nastavení si můžete upravit chování instalátoru (tichý režim, instalace pro všechny uživatele).</i></p>
        """
        text_area.setHtml(html_content)
        layout.addWidget(text_area)

        btn_ok = QPushButton("Rozumím")
        btn_ok.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ok.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['accent']}; color: white; border: none;
                padding: 10px; border-radius: 5px; font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {COLORS['accent_hover']}; }}
        """)
        btn_ok.clicked.connect(self.accept)
        layout.addWidget(btn_ok)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Univerzální aplikace")
        self.resize(1150, 750)
        
        # 1. IKONA
        icon_path = resource_path("program_icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        else:
            self.setWindowIcon(QIcon.fromTheme("system-software-install"))
        
        self.apply_custom_title_bar()

        try:
            self.setStyleSheet(styles.get_stylesheet())
        except Exception as e:
            print(f"Chyba stylů: {e}")

        # Hlavní kontejner
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ============================================================
        # 1. LEVÝ PANEL (SIDEBAR CONTAINER)
        # ============================================================
        sidebar_container = QWidget()
        sidebar_container.setFixedWidth(260)
        sidebar_container.setStyleSheet(f"background-color: {COLORS['bg_sidebar']}; border-right: 1px solid {COLORS['border']};")
        
        sidebar_layout = QVBoxLayout(sidebar_container)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # A) Horní seznam (Funkce)
        self.sidebar_list = QListWidget()
        self.sidebar_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.sidebar_list.setStyleSheet(f"""
            QListWidget {{ background-color: transparent; border: none; outline: none; margin-top: 10px; }}
            QListWidget::item {{ padding: 15px 10px; margin: 2px 10px; border-radius: 6px; color: {COLORS['sub_text']}; font-weight: 500; }}
            QListWidget::item:selected {{ background-color: {COLORS['item_bg']}; color: {COLORS['fg']}; border-left: 3px solid {COLORS['accent']}; }}
            QListWidget::item:hover {{ background-color: {COLORS['item_hover']}; color: {COLORS['fg']}; }}
        """)
        self.sidebar_list.currentRowChanged.connect(self.switch_main_page)
        
        self.add_sidebar_item("📦  Chytrá instalace aplikací")
        self.add_sidebar_item("🔄  Aktualizace aplikací")
        self.add_sidebar_item("🩺  Kontrola stavu PC")
        self.add_sidebar_item("🗑️  Odinstalace aplikací")
        
        sidebar_layout.addWidget(self.sidebar_list)

        # B) Spacer (Tlačí tlačítka dolů)
        sidebar_layout.addStretch()

        # C) Oddělovač
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background-color: {COLORS['border']}; margin: 10px 15px;")
        sidebar_layout.addWidget(sep)

        # D) Spodní tlačítka (Nastavení + Nápověda)
        bottom_buttons_layout = QHBoxLayout()
        bottom_buttons_layout.setContentsMargins(15, 0, 15, 20)
        bottom_buttons_layout.setSpacing(10)

        # Tlačítko Nastavení
        self.btn_settings = QPushButton("⚙️ Nastavení")
        self.btn_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_settings.setFixedHeight(40)
        self.btn_settings.clicked.connect(self.go_to_settings)
        self._style_bottom_btn(self.btn_settings)
        
        # Tlačítko Nápověda (Otazník)
        self.btn_help = QPushButton("❓")
        self.btn_help.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_help.setFixedSize(40, 40)
        self.btn_help.setToolTip("Vysvětlivka funkcí")
        self.btn_help.clicked.connect(self.show_help)
        self._style_bottom_btn(self.btn_help)

        bottom_buttons_layout.addWidget(self.btn_settings, stretch=1)
        bottom_buttons_layout.addWidget(self.btn_help, stretch=0)
        
        sidebar_layout.addLayout(bottom_buttons_layout)

        # Přidání sidebaru do hlavního okna
        main_layout.addWidget(sidebar_container)

        # ============================================================
        # 2. PRAVÝ OBSAH (PAGES)
        # ============================================================
        self.pages = QStackedWidget()
        main_layout.addWidget(self.pages)

        # Index 0: Installer
        self.pages.addWidget(InstallerPage())          
        # Index 1: Updater
        self.pages.addWidget(UpdaterPage())            
        # Index 2: Health
        self.pages.addWidget(HealthCheckPage())        
        # Index 3: Uninstaller
        try:
            self.pages.addWidget(UninstallerPage())    
        except Exception as e:
            self.pages.addWidget(QLabel(f"Chyba odinstalace: {e}"))
        
        # Index 4: Settings (Už není v listu nahoře)
        self.pages.addWidget(SettingsPage())           

        # Výchozí stav
        self.sidebar_list.setCurrentRow(0)

    # --- METODY ---

    def add_sidebar_item(self, text):
        item = QListWidgetItem(text)
        self.sidebar_list.addItem(item)

    def switch_main_page(self, index):
        """Přepíná mezi hlavními funkcemi (0-3)."""
        if index >= 0:
            self.pages.setCurrentIndex(index)
            # Resetovat styl tlačítka nastavení (aby nevypadalo aktivně)
            self._style_bottom_btn(self.btn_settings, active=False)
            self._style_bottom_btn(self.btn_help, active=False)

    def go_to_settings(self):
        """Přepne na stránku nastavení (Index 4) a odznačí seznam funkcí."""
        self.sidebar_list.clearSelection() # Zruší výběr nahoře
        self.pages.setCurrentIndex(4)      # Přepne na nastavení
        self._style_bottom_btn(self.btn_settings, active=True) # Zvýrazní tlačítko

    def show_help(self):
        """Otevře dialog s nápovědou."""
        dialog = HelpDialog(self)
        dialog.exec()

    def _style_bottom_btn(self, btn, active=False):
        """Styluje spodní tlačítka."""
        bg_color = COLORS['item_bg'] if active else "transparent"
        border = f"1px solid {COLORS['accent']}" if active else "none"
        text_color = "white" if active else COLORS['sub_text']
        
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_color};
                color: {text_color};
                border: {border};
                border-radius: 6px;
                font-weight: bold;
                text-align: center;
            }}
            QPushButton:hover {{
                background-color: {COLORS['item_hover']};
                color: white;
            }}
        """)

    def apply_custom_title_bar(self):
        """Tmavá lišta pro Windows 11/10."""
        try:
            hwnd = self.winId().__int__() 
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            DWMWA_CAPTION_COLOR = 35 
            DWMWA_TEXT_COLOR = 36
            
            windll.dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, byref(c_int(1)), 4)

            hex_color = COLORS['bg_sidebar']
            r = int(hex_color[1:3], 16)
            g = int(hex_color[3:5], 16)
            b = int(hex_color[5:7], 16)
            colorref = b << 16 | g << 8 | r

            windll.dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_CAPTION_COLOR, byref(c_int(colorref)), 4)
            
            white_ref = 255 << 16 | 255 << 8 | 255
            windll.dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_TEXT_COLOR, byref(c_int(white_ref)), 4)
        except Exception:
            pass

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    splash = SplashScreen()
    splash.show()

    if not is_admin():
        pass

    def start_main_app():
        global window
        window = MainWindow()
        window.show()
    
    splash.finished.connect(start_main_app)
    sys.exit(app.exec())