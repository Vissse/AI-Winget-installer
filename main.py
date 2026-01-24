import sys
import os
import ctypes
from ctypes import windll, byref, c_int
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QListWidget, QListWidgetItem, QStackedWidget, QPushButton, 
                             QFrame, QLabel, QStyledItemDelegate)
from PyQt6.QtCore import QSize, Qt, QTimer, QVariantAnimation, QRect, QPoint
from PyQt6.QtGui import QIcon, QPixmap, QColor, QFont, QTransform, QPainter

import styles
from config import COLORS

# Importy stránek
from view_home import HomePage
from view_specs import SpecsPage
from view_uninstaller import UninstallerPage
from view_installer import InstallerPage
from view_settings import SettingsPage
from view_health import HealthCheckPage
from view_updater import UpdaterPage
from view_queue import QueuePage
from splash import SplashScreen
import boot_system
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

# === DELEGÁT PRO KRESLENÍ BADGE A SEPARÁTORŮ ===
class SidebarDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        # 1. Detekce a vykreslení separátoru (UserRole == -1)
        if index.data(Qt.ItemDataRole.UserRole) == -1:
            painter.save()
            painter.setPen(QColor(COLORS['border']))
            # Vykreslíme linku přesně uprostřed vymezené výšky itemu
            y = option.rect.center().y()
            painter.drawLine(option.rect.left() + 15, y, option.rect.right() - 15, y)
            painter.restore()
            return

        # 2. Standardní vykreslení položky (zachová nativní CSS pohyb/padding)
        super().paint(painter, option, index)
        
        # 3. Vykreslení modrého badge (pokud jsou data k dispozici)
        count = index.data(Qt.ItemDataRole.UserRole + 1)
        if count and count > 0:
            count_str = str(count)
            painter.save()
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            font = painter.font()
            font.setBold(True)
            font.setPointSize(9) # Fixní velikost proti chybám v konzoli
            painter.setFont(font)
            
            fm = painter.fontMetrics()
            tw = fm.horizontalAdvance(count_str)
            th = fm.height()
            
            padding_h, padding_v = 7, 2
            bw = max(th + padding_v * 2, tw + padding_h * 2)
            bh = th + padding_v * 2
            
            # Umístění badge na pravý okraj řádku
            badge_rect = QRect(
                option.rect.right() - bw - 15,
                option.rect.top() + (option.rect.height() - bh) // 2,
                bw, bh
            )
            
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(COLORS['accent']))
            painter.drawRoundedRect(badge_rect, bh / 2, bh / 2)
            
            painter.setPen(QColor("white"))
            painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, count_str)
            painter.restore()

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

        # === SIDEBAR ===
        sidebar_container = QWidget()
        sidebar_container.setFixedWidth(260)
        sidebar_container.setStyleSheet(f"background-color: {COLORS['bg_sidebar']}; border-right: 1px solid {COLORS['border']};")
        sidebar_layout = QVBoxLayout(sidebar_container)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        self.sidebar_list = QListWidget()
        self.sidebar_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.sidebar_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.sidebar_list.setItemDelegate(SidebarDelegate(self.sidebar_list))
        
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
                padding-left: 15px;
            }}
            QListWidget::item:hover {{ 
                background-color: {COLORS['item_hover']}; 
                color: {COLORS['fg']}; 
            }}
        """)
        
        self.sidebar_list.setIconSize(QSize(24, 24))
        self.sidebar_list.itemClicked.connect(self.on_sidebar_click)
        
        # Skladba menu
        self.add_sidebar_item("Přehled", "house-simple-thin.png", 0)
        self.add_sidebar_separator()
        
        self.add_sidebar_item("Hledat balíčky", "package-thin.png", 1)
        self.add_sidebar_item("Instalační fronta", "tray-arrow-down-thin.png", 7)
        self.add_sidebar_separator()
        
        self.add_sidebar_item("Aktualizace aplikací", "arrows-clockwise-thin.png", 2)
        self.add_sidebar_item("Odinstalace aplikací", "trash-simple-thin.png", 4)
        self.add_sidebar_separator()
        
        self.add_sidebar_item("Kontrola stavu PC", "heartbeat-thin.png", 3)
        self.add_sidebar_item("Specifikace PC", "desktop-thin.png", 6)
        
        sidebar_layout.addWidget(self.sidebar_list)
        sidebar_layout.addSpacing(20) 

        # Tlačítko Nastavení
        sep_frame = QFrame()
        sep_frame.setFrameShape(QFrame.Shape.HLine)
        sep_frame.setFixedHeight(1)
        sep_frame.setStyleSheet(f"background-color: {COLORS['border']}; margin: 0 15px;")
        sidebar_layout.addWidget(sep_frame)
        sidebar_layout.addSpacing(10)

        self.btn_settings = QPushButton(" Nastavení")
        self.btn_settings.setIcon(QIcon("images/gear-thin.png"))
        self.btn_settings.setIconSize(QSize(20, 20))
        self.btn_settings.setFixedHeight(40)
        self.btn_settings.clicked.connect(self.go_to_settings)
        self._style_bottom_btn(self.btn_settings)

        btn_container = QHBoxLayout()
        btn_container.setContentsMargins(15, 0, 15, 20)
        btn_container.addWidget(self.btn_settings)
        sidebar_layout.addLayout(btn_container)

        main_layout.addWidget(sidebar_container)

        # === STRÁNKY ===
        self.pages = QStackedWidget()
        main_layout.addWidget(self.pages)
        
        self.queue_page = QueuePage()
        self.updater_page = UpdaterPage()
        self.installer_page = InstallerPage(self.queue_page)
        self.queue_page.set_installer_ref(self.installer_page)
        
        self.pages.addWidget(HomePage())         # 0
        self.pages.addWidget(self.installer_page) # 1
        self.pages.addWidget(self.updater_page)  # 2
        self.pages.addWidget(HealthCheckPage())  # 3
        self.pages.addWidget(UninstallerPage())  # 4
        self.pages.addWidget(SettingsPage(updater=self.updater)) # 5
        self.pages.addWidget(SpecsPage())        # 6
        self.pages.addWidget(self.queue_page)    # 7
        
        self.navigate_to_page(0)

        # === ANIMACE ===
        self.rotation_anim = QVariantAnimation(self)
        self.rotation_anim.setDuration(1200)
        self.rotation_anim.setStartValue(0)
        self.rotation_anim.setEndValue(360)
        self.rotation_anim.setLoopCount(-1)
        self.rotation_anim.valueChanged.connect(self.rotate_sidebar_icon)

        self.updater_page.scan_finished_signal.connect(self.update_sidebar_badge)
        QTimer.singleShot(2000, self.start_initial_scan)

    def start_initial_scan(self):
        self.rotation_anim.start()
        self.updater_page.scan_updates()

    def rotate_sidebar_icon(self, angle):
        for i in range(self.sidebar_list.count()):
            item = self.sidebar_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == 2:
                pix = QPixmap("images/arrows-clockwise-thin.png")
                if pix.isNull(): return
                canvas = QPixmap(32, 32)
                canvas.fill(Qt.GlobalColor.transparent)
                p = QPainter(canvas)
                p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
                p.translate(16, 16)
                p.rotate(angle)
                rect = QRect(-12, -12, 24, 24)
                p.drawPixmap(rect, pix)
                p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
                p.fillRect(rect, QColor(COLORS['accent']))
                p.end()
                item.setIcon(QIcon(canvas))
                break

    def update_sidebar_badge(self, updates):
        self.rotation_anim.stop()
        count = len(updates)
        for i in range(self.sidebar_list.count()):
            item = self.sidebar_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == 2:
                item.setIcon(QIcon("images/arrows-clockwise-thin.png"))
                item.setData(Qt.ItemDataRole.UserRole + 1, count)
                if count > 0: item.setForeground(QColor(COLORS['fg']))
                else: item.setForeground(QColor(COLORS['sub_text']))
                break

    def add_sidebar_item(self, text, icon, index):
        item = QListWidgetItem(text)
        item.setData(Qt.ItemDataRole.UserRole, index)
        item.setData(Qt.ItemDataRole.UserRole + 1, 0)
        if os.path.exists(os.path.join("images", icon)):
            item.setIcon(QIcon(os.path.join("images", icon)))
        self.sidebar_list.addItem(item)

    def add_sidebar_separator(self):
        item = QListWidgetItem("")
        item.setData(Qt.ItemDataRole.UserRole, -1) # Kód pro separátor v delegátovi
        item.setFlags(Qt.ItemFlag.NoItemFlags)
        item.setSizeHint(QSize(0, 20)) # Pevná výška mezery
        self.sidebar_list.addItem(item)

    def on_sidebar_click(self, item):
        idx = item.data(Qt.ItemDataRole.UserRole)
        if idx is not None and idx != -1: self.navigate_to_page(idx)

    def navigate_to_page(self, index):
        for i in range(self.sidebar_list.count()):
            if self.sidebar_list.item(i).data(Qt.ItemDataRole.UserRole) == index:
                self.sidebar_list.setCurrentRow(i)
                break
        self.pages.setCurrentIndex(index)
        self._style_bottom_btn(self.btn_settings, active=(index == 5))

    def go_to_settings(self):
        self.sidebar_list.clearSelection()
        self.navigate_to_page(5)

    def _style_bottom_btn(self, btn, active=False):
        bg = COLORS['item_bg'] if active else "transparent"
        tx = "white" if active else COLORS['sub_text']
        br = f"border-bottom: 3px solid {COLORS['accent']};" if active else "border: none;"
        btn.setStyleSheet(f"QPushButton {{ background: {bg}; color: {tx}; {br} border-radius: 6px; font-weight: bold; text-align: left; padding-left: 15px; }} QPushButton:hover {{ background: {COLORS['item_hover']}; }}")

    def apply_custom_title_bar(self):
        try:
            hwnd = self.winId().__int__()
            windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, byref(c_int(1)), 4)
        except: pass

if __name__ == "__main__":
    # 1. Boot Checks
    try:
        import boot_system
        boot_system.perform_boot_checks()
    except ImportError: pass

    app = QApplication(sys.argv)
    splash = SplashScreen()
    splash.show()
    
    def start_program():
        global window
        # Vytvoříme okno skryté
        window = MainWindow()
        
        # Funkce pro zobrazení
        def launch_app_interface():
            window.show()

        # Spustíme kontrolu. Pokud uživatel dá "Později", zavolá se launch_app_interface
        window.updater.check_for_updates(silent=True, on_continue=launch_app_interface)

    splash.finished.connect(start_program)
    sys.exit(app.exec())