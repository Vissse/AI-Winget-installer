import sys
import os
import ctypes
from ctypes import windll, byref, c_int
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QListWidget, QListWidgetItem, QStackedWidget, QMessageBox, QLabel, 
                             QPushButton, QDialog, QTextEdit, QFrame)
from PyQt6.QtCore import QSize, Qt, QTimer
from PyQt6.QtGui import QIcon, QFont, QMouseEvent

import styles
from config import COLORS

# Importy stránek
from view_uninstaller import UninstallerPage
from view_installer import InstallerPage
from view_settings import SettingsPage
from view_health import HealthCheckPage
from view_updater import UpdaterPage
from splash import SplashScreen

# NOVÝ IMPORT PRO LOGIKU AKTUALIZACÍ
from updater import AppUpdater

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

# --- OKNO S NÁPOVĚDOU (MODERNÍ DESIGN) ---
class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(600, 520)
        
        # Hlavní kontejner
        self.container = QWidget(self)
        self.container.setGeometry(0, 0, 600, 520)
        self.container.setStyleSheet("background: transparent; border: none;")
        
        main_layout = QVBoxLayout(self.container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. HORNÍ LIŠTA
        title_bar = QWidget()
        title_bar.setFixedHeight(45)
        title_bar.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS['bg_sidebar']};
                border: 1px solid {COLORS['border']};
                border-bottom: 1px solid {COLORS['border']};
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                border-bottom-left-radius: 0px;
                border-bottom-right-radius: 0px;
            }}
        """)
        
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(15, 0, 0, 0) 
        
        lbl_title = QLabel("📖  Průvodce aplikací")
        lbl_title.setStyleSheet("color: white; font-weight: bold; font-size: 14px; border: none; background: transparent;")
        title_layout.addWidget(lbl_title)
        
        title_layout.addStretch()
        
        # Tlačítko zavřít (X)
        btn_close_x = QPushButton("\uE8BB") 
        btn_close_x.setFixedSize(46, 44) 
        btn_close_x.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close_x.clicked.connect(self.reject)
        
        btn_close_x.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #cccccc;
                border: none;
                border-top-right-radius: 7px;
                font-family: 'Segoe MDL2 Assets';
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #e81123;
                color: white;
            }
            QPushButton:pressed {
                background-color: #b00b1a;
                color: white;
            }
        """)
        title_layout.addWidget(btn_close_x)
        
        main_layout.addWidget(title_bar)

        # 2. OBSAH OKNA
        content_widget = QWidget()
        content_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS['bg_main']};
                border-left: 1px solid {COLORS['border']};
                border-right: 1px solid {COLORS['border']};
                border-bottom: 1px solid {COLORS['border']};
                border-top: none;
                border-bottom-left-radius: 8px;
                border-bottom-right-radius: 8px;
                border-top-left-radius: 0px;
                border-top-right-radius: 0px;
            }}
        """)
        
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(20, 20, 20, 20)
        
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
            QScrollBar:vertical {{
                border: none; background-color: {COLORS['bg_sidebar']}; width: 8px; margin: 0px; border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background-color: #444; min-height: 20px; border-radius: 4px;
            }}
            QScrollBar::handle:vertical:hover {{ background-color: {COLORS['accent']}; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
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
        content_layout.addWidget(text_area)

        btn_ok = QPushButton("Rozumím")
        btn_ok.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ok.setFixedHeight(40)
        btn_ok.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['accent']}; color: white; border: none;
                border-radius: 6px; font-weight: bold; font-size: 14px;
            }}
            QPushButton:hover {{ background-color: {COLORS['accent_hover']}; }}
        """)
        btn_ok.clicked.connect(self.accept)
        content_layout.addWidget(btn_ok)

        main_layout.addWidget(content_widget)
        
        self.old_pos = None

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            if event.position().y() <= 50:
                self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.old_pos:
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.pos() + delta)
            self.old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self.old_pos = None

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Univerzální aplikace")
        self.resize(1150, 750)
        
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

        # === 1. INICIALIZACE UPDATERU ===
        self.updater = AppUpdater(self)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # LEVÝ PANEL
        sidebar_container = QWidget()
        sidebar_container.setFixedWidth(260)
        sidebar_container.setStyleSheet(f"background-color: {COLORS['bg_sidebar']}; border-right: 1px solid {COLORS['border']};")
        
        sidebar_layout = QVBoxLayout(sidebar_container)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

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
        sidebar_layout.addStretch()

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background-color: {COLORS['border']}; margin: 10px 15px;")
        sidebar_layout.addWidget(sep)

        bottom_buttons_layout = QHBoxLayout()
        bottom_buttons_layout.setContentsMargins(15, 0, 15, 20)
        bottom_buttons_layout.setSpacing(10)

        self.btn_settings = QPushButton("⚙️ Nastavení")
        self.btn_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_settings.setFixedHeight(40)
        self.btn_settings.clicked.connect(self.go_to_settings)
        self._style_bottom_btn(self.btn_settings)
        
        self.btn_help = QPushButton("❓")
        self.btn_help.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_help.setFixedSize(40, 40)
        self.btn_help.setToolTip("Vysvětlivka funkcí")
        self.btn_help.clicked.connect(self.show_help)
        self._style_bottom_btn(self.btn_help)

        bottom_buttons_layout.addWidget(self.btn_settings, stretch=1)
        bottom_buttons_layout.addWidget(self.btn_help, stretch=0)
        sidebar_layout.addLayout(bottom_buttons_layout)
        main_layout.addWidget(sidebar_container)

        # PRAVÝ OBSAH
        self.pages = QStackedWidget()
        main_layout.addWidget(self.pages)

        self.pages.addWidget(InstallerPage())          
        self.pages.addWidget(UpdaterPage())            
        self.pages.addWidget(HealthCheckPage())        
        try: self.pages.addWidget(UninstallerPage())    
        except Exception as e: self.pages.addWidget(QLabel(f"Chyba: {e}"))
        
        # === 2. PŘEDÁNÍ UPDATERU DO NASTAVENÍ ===
        self.pages.addWidget(SettingsPage(updater=self.updater))           

        self.sidebar_list.setCurrentRow(0)
        
        # === 3. AUTOMATICKÁ KONTROLA PO STARTU (s odkladem 2s) ===
        QTimer.singleShot(2000, lambda: self.updater.check_for_updates(silent=True))

    def add_sidebar_item(self, text):
        item = QListWidgetItem(text)
        self.sidebar_list.addItem(item)

    def switch_main_page(self, index):
        if index >= 0:
            self.pages.setCurrentIndex(index)
            self._style_bottom_btn(self.btn_settings, active=False)
            self._style_bottom_btn(self.btn_help, active=False)

    def go_to_settings(self):
        self.sidebar_list.clearSelection()
        self.pages.setCurrentIndex(4)
        self._style_bottom_btn(self.btn_settings, active=True)

    def show_help(self):
        dialog = HelpDialog(self)
        dialog.exec()

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
    app = QApplication(sys.argv)
    splash = SplashScreen()
    splash.show()
    
    if not is_admin(): 
        pass # Zde by mohla být admin logika

    def start_program():
        global window
        # 1. Vytvoříme okno, ale NEZOBRAZÍME HO (hide)
        window = MainWindow()
        
        # 2. Definujeme funkci, která se zavolá, až bude bezpečné spustit aplikaci
        # (buď není update, nebo ho uživatel odmítl)
        def launch_app_interface():
            window.show()

        # 3. Spustíme kontrolu aktualizací
        # Aplikace čeká (splash se zavře, nic není vidět, jen případný popup aktualizace)
        # Pokud update není, okamžitě se zavolá launch_app_interface
        window.updater.check_for_updates(silent=True, on_continue=launch_app_interface)

    # Po dokončení splashe se zavolá start_program
    splash.finished.connect(start_program)
    
    sys.exit(app.exec())