import sys
import os
import ctypes
from ctypes import windll, byref, c_int
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QListWidget, QListWidgetItem, QStackedWidget, QPushButton, 
                             QFrame, QLabel, QStyledItemDelegate, QStyle)
from PyQt6.QtCore import QSize, Qt, QTimer, QVariantAnimation, QRect, QPoint
from PyQt6.QtGui import QIcon, QPixmap, QColor, QFont, QPainter, QPainterPath

import styles
from config import COLORS, resource_path

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

# === LIST WIDGET S DETEKCÍ POHYBU ===
class AnimatedListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.last_hovered_row = -1

    def mouseMoveEvent(self, event):
        index = self.indexAt(event.pos())
        row = index.row()
        
        if row != self.last_hovered_row:
            delegate = self.itemDelegate()
            if delegate:
                # Schování starého hoveru
                if self.last_hovered_row != -1 and self.last_hovered_row != self.currentRow():
                    delegate.start_fade_animation(self.last_hovered_row, 1.0, 0.0, self)
                # Spuštění nového hoveru
                if row != -1 and row != self.currentRow():
                    delegate.start_fade_animation(row, 0.0, 1.0, self)
            self.last_hovered_row = row
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        delegate = self.itemDelegate()
        if delegate:
            for row in list(delegate.animations.keys()):
                if row != self.currentRow():
                    delegate.start_fade_animation(row, delegate.animations.get(row, 0.0), 0.0, self)
        self.last_hovered_row = -1
        super().leaveEvent(event)

# === DELEGÁT S ANIMACÍ VÝŠKY I PRŮHLEDNOSTI ===
class SidebarDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.animations = {} 
        self._active_anims = {}

    def start_fade_animation(self, row, start, end, widget):
        if row == -1: return
        if row in self._active_anims:
            self._active_anims[row].stop()

        anim = QVariantAnimation(widget)
        anim.setDuration(250) # Délka animace pro plynulý růst
        anim.setStartValue(start)
        anim.setEndValue(end)
        anim.valueChanged.connect(lambda val: self._update_val(row, val, widget))
        self._active_anims[row] = anim
        anim.start()

    def _update_val(self, row, val, widget):
        self.animations[row] = val
        widget.update()

    def paint(self, painter, option, index):
        if index.data(Qt.ItemDataRole.UserRole) == -1:
            painter.save()
            painter.setPen(QColor(COLORS['border']))
            y = option.rect.center().y()
            painter.drawLine(option.rect.left() + 15, y, option.rect.right() - 15, y)
            painter.restore()
            return

        super().paint(painter, option, index)
        
        is_selected = option.state & QStyle.StateFlag.State_Selected
        # Pokud je vybraný, anim_value je 1.0, jinak se bere animace hoveru
        anim_value = 1.0 if is_selected else self.animations.get(index.row(), 0.0)

        if anim_value > 0:
            painter.save()
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Definice kontejneru itemu (odpovídá marginům v CSS)
            rect = option.rect.adjusted(10, 2, -10, -2)
            radius = 6
            
            # Barva s plynulým zesvětlením
            color = QColor(COLORS['accent'])
            color.setAlpha(int(255 * anim_value))
            painter.setBrush(color)
            painter.setPen(Qt.PenStyle.NoPen)
            
            # ANIMACE VÝŠKY: Proužek roste od středu
            h = rect.height() * anim_value
            y = rect.y() + (rect.height() - h) / 2
            
            # Maska pro zaoblení (Clip Path)
            path = QPainterPath()
            path.addRoundedRect(float(rect.x()), float(rect.y()), float(rect.width()), float(rect.height()), float(radius), float(radius))
            painter.setClipPath(path)
            
            # Vykreslení proužku (šířka 4px, animovaná výška y a h)
            painter.drawRect(QRect(rect.x(), int(y), 4, int(h)))
            painter.restore()

        # Badge
        count = index.data(Qt.ItemDataRole.UserRole + 1)
        if count and count > 0:
            self._draw_badge(painter, option, str(count))

    def _draw_badge(self, painter, option, count_str):
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        font = painter.font()
        font.setBold(True); font.setPointSize(9)
        painter.setFont(font)
        fm = painter.fontMetrics()
        tw = fm.horizontalAdvance(count_str)
        badge_rect = QRect(option.rect.right() - 45, option.rect.top() + (option.rect.height() - 18) // 2, tw + 14, 18)
        painter.setPen(Qt.PenStyle.NoPen); painter.setBrush(QColor(COLORS['accent']))
        painter.drawRoundedRect(badge_rect, 9, 9)
        painter.setPen(QColor("white")); painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, count_str)
        painter.restore()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Univerzální aplikace"); self.resize(1150, 750)
        icon_path = resource_path("program_icon.png")
        if os.path.exists(icon_path): self.setWindowIcon(QIcon(icon_path))
        
        self.apply_custom_title_bar()
        try: self.setStyleSheet(styles.get_stylesheet())
        except: pass

        self.updater = AppUpdater(self)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0); main_layout.setSpacing(0)

        # === SIDEBAR ===
        sidebar_container = QWidget()
        sidebar_container.setFixedWidth(260)
        sidebar_container.setStyleSheet(f"background-color: {COLORS['bg_sidebar']}; border-right: 1px solid {COLORS['border']};")
        sidebar_layout = QVBoxLayout(sidebar_container)
        sidebar_layout.setContentsMargins(0, 0, 0, 0); sidebar_layout.setSpacing(0)

        self.sidebar_list = AnimatedListWidget()
        self.sidebar_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.sidebar_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.sidebar_delegate = SidebarDelegate(self.sidebar_list)
        self.sidebar_list.setItemDelegate(self.sidebar_delegate)
        
        self.sidebar_list.setStyleSheet(f"""
            QListWidget {{ background-color: transparent; border: none; outline: none; margin-top: 15px; }}
            QListWidget::item {{ 
                padding: 12px 10px; margin: 2px 10px; border-radius: 6px; 
                color: {COLORS['sub_text']}; font-weight: 500; 
            }}
            QListWidget::item:selected {{ background-color: {COLORS['item_bg']}; color: {COLORS['fg']}; border-left: none; }}
            QListWidget::item:hover {{ background-color: {COLORS['item_hover']}; color: {COLORS['fg']}; }}
        """)
        
        self.sidebar_list.setIconSize(QSize(24, 24))
        self.sidebar_list.itemSelectionChanged.connect(self.on_selection_changed)
        self.sidebar_list.itemClicked.connect(self.on_sidebar_click)
        
        self.add_sidebar_item("Přehled", "images/house-simple-thin.png", 0)
        self.add_sidebar_separator()
        self.add_sidebar_item("Hledat balíčky", "images/package-thin.png", 1)
        self.add_sidebar_item("Instalační fronta", "images/tray-arrow-down-thin.png", 7)
        self.add_sidebar_separator()
        self.add_sidebar_item("Aktualizace aplikací", "images/arrows-clockwise-thin.png", 2)
        self.add_sidebar_item("Odinstalace aplikací", "images/trash-simple-thin.png", 4)
        self.add_sidebar_separator()
        self.add_sidebar_item("Kontrola stavu PC", "images/heartbeat-thin.png", 3)
        self.add_sidebar_item("Specifikace PC", "images/desktop-thin.png", 6)
        
        sidebar_layout.addWidget(self.sidebar_list)
        sidebar_layout.addSpacing(20) 

        sep_frame = QFrame(); sep_frame.setFrameShape(QFrame.Shape.HLine); sep_frame.setFixedHeight(1)
        sep_frame.setStyleSheet(f"background-color: {COLORS['border']}; margin: 0 15px;")
        sidebar_layout.addWidget(sep_frame); sidebar_layout.addSpacing(10)

        self.btn_settings = QPushButton(" Nastavení")
        self.btn_settings.setIcon(QIcon(resource_path("images/gear-thin.png")))
        self.btn_settings.setIconSize(QSize(20, 20)); self.btn_settings.setFixedHeight(40)
        self.btn_settings.clicked.connect(self.go_to_settings); self._style_bottom_btn(self.btn_settings)

        btn_container = QHBoxLayout(); btn_container.setContentsMargins(15, 0, 15, 20); btn_container.addWidget(self.btn_settings)
        sidebar_layout.addLayout(btn_container); main_layout.addWidget(sidebar_container)

        self.pages = QStackedWidget(); main_layout.addWidget(self.pages)
        self.queue_page = QueuePage(); self.updater_page = UpdaterPage()
        self.installer_page = InstallerPage(self.queue_page); self.queue_page.set_installer_ref(self.installer_page)
        
        self.pages.addWidget(HomePage()); self.pages.addWidget(self.installer_page) 
        self.pages.addWidget(self.updater_page); self.pages.addWidget(HealthCheckPage())  
        self.pages.addWidget(UninstallerPage()); self.pages.addWidget(SettingsPage(updater=self.updater)) 
        self.pages.addWidget(SpecsPage()); self.pages.addWidget(self.queue_page)    
        
        self.navigate_to_page(0)

        self.rotation_anim = QVariantAnimation(self); self.rotation_anim.setDuration(1200)
        self.rotation_anim.setStartValue(0); self.rotation_anim.setEndValue(360); self.rotation_anim.setLoopCount(-1)
        self.rotation_anim.valueChanged.connect(self.rotate_sidebar_icon)
        self.updater_page.scan_finished_signal.connect(self.update_sidebar_badge)
        QTimer.singleShot(2000, self.start_initial_scan)

    def on_selection_changed(self):
        for row in list(self.sidebar_delegate.animations.keys()):
            if row != self.sidebar_list.currentRow(): self.sidebar_delegate.animations[row] = 0.0
        self.sidebar_list.update()

    def start_initial_scan(self):
        self.rotation_anim.start(); self.updater_page.scan_updates()

    def rotate_sidebar_icon(self, angle):
        for i in range(self.sidebar_list.count()):
            item = self.sidebar_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == 2:
                pix = QPixmap(resource_path("images/arrows-clockwise-thin.png"))
                if pix.isNull(): return
                canvas = QPixmap(32, 32); canvas.fill(Qt.GlobalColor.transparent)
                p = QPainter(canvas); p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
                p.translate(16, 16); p.rotate(angle); rect = QRect(-12, -12, 24, 24); p.drawPixmap(rect, pix)
                p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn); p.fillRect(rect, QColor(COLORS['accent'])); p.end()
                item.setIcon(QIcon(canvas)); break

    def update_sidebar_badge(self, updates):
        self.rotation_anim.stop(); count = len(updates)
        for i in range(self.sidebar_list.count()):
            item = self.sidebar_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == 2:
                item.setIcon(QIcon(resource_path("images/arrows-clockwise-thin.png")))
                item.setData(Qt.ItemDataRole.UserRole + 1, count); break

    def add_sidebar_item(self, text, icon_relative_path, index):
        item = QListWidgetItem(text); item.setData(Qt.ItemDataRole.UserRole, index); item.setData(Qt.ItemDataRole.UserRole + 1, 0)
        full_icon_path = resource_path(icon_relative_path)
        if os.path.exists(full_icon_path): item.setIcon(QIcon(full_icon_path))
        self.sidebar_list.addItem(item)
        
    def add_sidebar_separator(self):
        item = QListWidgetItem(""); item.setData(Qt.ItemDataRole.UserRole, -1) 
        item.setFlags(Qt.ItemFlag.NoItemFlags); item.setSizeHint(QSize(0, 20)); self.sidebar_list.addItem(item)

    def on_sidebar_click(self, item):
        idx = item.data(Qt.ItemDataRole.UserRole)
        if idx is not None and idx != -1: self.navigate_to_page(idx)

    def navigate_to_page(self, index):
        for i in range(self.sidebar_list.count()):
            if self.sidebar_list.item(i).data(Qt.ItemDataRole.UserRole) == index:
                self.sidebar_list.setCurrentRow(i); break
        self.pages.setCurrentIndex(index); self._style_bottom_btn(self.btn_settings, active=(index == 5))

    def go_to_settings(self): self.sidebar_list.clearSelection(); self.navigate_to_page(5)

    def _style_bottom_btn(self, btn, active=False):
        bg = COLORS['item_bg'] if active else "transparent"; tx = "white" if active else COLORS['sub_text']
        br = f"border-bottom: 3px solid {COLORS['accent']};" if active else "border: none;"
        btn.setStyleSheet(f"QPushButton {{ background: {bg}; color: {tx}; {br} border-radius: 6px; font-weight: bold; text-align: left; padding-left: 15px; }} QPushButton:hover {{ background: {COLORS['item_hover']}; }}")

    def apply_custom_title_bar(self):
        try:
            hwnd = self.winId().__int__()
            windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, byref(c_int(1)), 4)
            color_hex = COLORS['bg_sidebar'].lstrip('#')
            r, g, b = int(color_hex[0:2], 16), int(color_hex[2:4], 16), int(color_hex[4:6], 16)
            dwm_color = (b << 16) | (g << 8) | r
            windll.dwmapi.DwmSetWindowAttribute(hwnd, 35, byref(c_int(dwm_color)), 4)
            windll.dwmapi.DwmSetWindowAttribute(hwnd, 36, byref(c_int(0x00FFFFFF)), 4)
        except: pass

if __name__ == "__main__":
    app = QApplication(sys.argv)
    splash = SplashScreen(); splash.show()
    def start_program():
        global window
        window = MainWindow()
        window.updater.check_for_updates(silent=True, on_continue=window.show)
    splash.finished.connect(start_program)
    sys.exit(app.exec())