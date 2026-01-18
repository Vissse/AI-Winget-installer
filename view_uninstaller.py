import winreg
import os
import requests
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget, QListWidgetItem, QLineEdit, QMessageBox, QFileIconProvider)
from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal, QFileInfo
from PyQt6.QtGui import QPixmap, QImage, QIcon

from workers import WingetListWorker, UninstallWorker
from config import COLORS

# --- 1. WORKER PRO NAČÍTÁNÍ IKON (LOKÁLNÍ I ONLINE) ---
class LocalIconWorker(QThread):
    loaded = pyqtSignal(QPixmap)

    def __init__(self, app_id, app_name, known_paths=None):
        super().__init__()
        self.app_id = app_id
        self.app_name = app_name
        self.known_paths = known_paths or {}

    def run(self):
        # A) ZKUSÍME NAJÍT LOKÁLNÍ IKONU Z REGISTRŮ
        # Pokud máme cestu z registrů (DisplayIcon), použijeme ji
        if self.app_id in self.known_paths:
            icon_path = self.known_paths[self.app_id]
            pixmap = self.extract_local_icon(icon_path)
            if pixmap:
                self.loaded.emit(pixmap)
                return

        # B) FALLBACK: ONLINE HLEDÁNÍ (pokud lokální selže)
        # ... (stejná logika jako dříve pro online ikony) ...
        self.try_online_search()

    def extract_local_icon(self, path):
        """Vytáhne ikonku přímo z .exe nebo .ico souboru na disku."""
        try:
            # Registry často vrací cestu i s indexem, např: "C:\Program Files\App\app.exe,0"
            clean_path = path.split(',')[0].strip().replace('"', '')
            
            if os.path.exists(clean_path):
                # Použijeme Qt FileIconProvider, který si sáhne do systému
                file_info = QFileInfo(clean_path)
                icon_provider = QFileIconProvider()
                icon = icon_provider.icon(file_info)
                
                if not icon.isNull():
                    # Získáme pixmapu v požadované velikosti
                    return icon.pixmap(32, 32)
        except:
            pass
        return None

    def try_online_search(self):
        """Původní logika stahování z GitHubu pro aplikace bez záznamu v registrech."""
        urls_to_try = []
        clean_id = self.app_id
        lower_id = self.app_id.lower()
        dashed_id = lower_id.replace(".", "-")
        short_id = self.app_id.split(".")[-1].lower() if "." in self.app_id else lower_id

        base_dash = "https://cdn.jsdelivr.net/gh/walkxcode/dashboard-icons/png"
        base_uniget = "https://raw.githubusercontent.com/marticliment/UnigetUI/main/src/UnigetUI.PackageEngine/Assets/Packages"
        
        urls_to_try.append(f"{base_dash}/{dashed_id}.png")
        urls_to_try.append(f"{base_dash}/{lower_id}.png")
        urls_to_try.append(f"{base_dash}/{short_id}.png")
        urls_to_try.append(f"{base_uniget}/{clean_id}.png")

        session = requests.Session()
        for url in urls_to_try:
            try:
                response = session.get(url, timeout=1.5)
                if response.status_code == 200 and len(response.content) > 100:
                    image = QImage()
                    image.loadFromData(response.content)
                    if not image.isNull():
                        pixmap = QPixmap.fromImage(image)
                        pixmap = pixmap.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                        self.loaded.emit(pixmap)
                        return
            except:
                continue

# --- 2. HLEDÁNÍ CEST V REGISTRECH ---
def scan_registry_for_icons():
    """Projde registry a vrátí slovník {Nazev_Aplikace: Cesta_k_ikone}."""
    apps_icons = {}
    registry_paths = [
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"
    ]
    
    # Procházíme HKLM (System) i HKCU (User)
    roots = [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]

    for root in roots:
        for reg_path in registry_paths:
            try:
                key = winreg.OpenKey(root, reg_path)
                for i in range(0, winreg.QueryInfoKey(key)[0]):
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        subkey = winreg.OpenKey(key, subkey_name)
                        
                        # Získáme jméno a cestu k ikoně
                        try:
                            display_name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                            # Zkusíme najít DisplayIcon, pokud není, zkusíme InstallLocation + exe
                            display_icon = None
                            try:
                                display_icon = winreg.QueryValueEx(subkey, "DisplayIcon")[0]
                            except FileNotFoundError:
                                pass
                            
                            # Pokud máme ikonku, uložíme si ji. Klíčem je Název aplikace (ne ID),
                            # protože winget list často vrací ID, které v registrech není přímo klíčem.
                            if display_name and display_icon:
                                apps_icons[display_name.lower()] = display_icon
                                
                                # Také uložíme pod Winget ID, pokud ho v registrech najdeme (někdy tam je)
                                # Většinou je klíč registru shodný s ID produktu
                                apps_icons[subkey_name.lower()] = display_icon

                        except FileNotFoundError:
                            pass
                        finally:
                            winreg.CloseKey(subkey)
                    except:
                        continue
                winreg.CloseKey(key)
            except:
                continue
    return apps_icons


# --- 3. POLOŽKA SEZNAMU (WIDGET) ---
class AppItemWidget(QWidget):
    def __init__(self, name, app_id, parent_view, known_paths):
        super().__init__()
        self.app_id = app_id
        self.parent_view = parent_view
        
        self.setStyleSheet("background-color: transparent;")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 8, 15, 8)
        layout.setSpacing(15)
        
        # A) IKONA
        self.icon_lbl = QLabel()
        self.icon_lbl.setFixedSize(32, 32)
        self.icon_lbl.setText("📦") 
        self.icon_lbl.setStyleSheet("font-size: 22px; color: #888; border: none; background: transparent;")
        self.icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.icon_lbl)

        # Zkusíme najít cestu v registrech podle ID nebo Názvu
        # Winget ID se nemusí shodovat s registry, ale Name často ano
        matched_path = known_paths.get(app_id.lower()) or known_paths.get(name.lower())
        
        # Předáme workeru nalezenou cestu (pokud existuje)
        temp_paths_dict = {app_id: matched_path} if matched_path else {}

        self.icon_worker = LocalIconWorker(app_id, name, temp_paths_dict)
        self.icon_worker.loaded.connect(self.set_icon)
        self.icon_worker.start()
        
        # B) NÁZEV
        name_lbl = QLabel(name)
        name_lbl.setStyleSheet(f"font-weight: bold; font-size: 14px; color: {COLORS['fg']}; border: none;")
        layout.addWidget(name_lbl)
        
        layout.addStretch()
        
        # C) TLAČÍTKO
        btn = QPushButton("Odinstalovat")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {COLORS['sub_text']};
                border: none;
                font-weight: bold;
                font-size: 13px;
                text-align: right;
                padding: 5px;
            }}
            QPushButton:hover {{
                color: {COLORS['accent']};
                text-decoration: underline;
            }}
            QPushButton:pressed {{
                color: {COLORS['accent_hover']};
            }}
        """)
        btn.clicked.connect(self.on_uninstall)
        layout.addWidget(btn)

    def set_icon(self, pixmap):
        self.icon_lbl.setPixmap(pixmap)
        self.icon_lbl.setText("")

    def on_uninstall(self):
        self.parent_view.confirm_uninstall(self.app_id)


# --- 4. HLAVNÍ STRÁNKA (UNINSTALLER) ---
class UninstallerPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        # Header
        header = QHBoxLayout()
        title = QLabel("Odinstalace aplikací")
        title.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {COLORS['fg']};")
        header.addWidget(title)
        header.addStretch()
        
        self.search = QLineEdit()
        self.search.setPlaceholderText("Hledat aplikaci...")
        self.search.setFixedWidth(300)
        self.search.setStyleSheet(f"""
            QLineEdit {{ 
                background-color: {COLORS['input_bg']}; 
                border: 1px solid {COLORS['border']};
                padding: 8px; border-radius: 4px; color: {COLORS['fg']};
            }}
            QLineEdit:focus {{ border: 1px solid {COLORS['accent']}; }}
        """)
        self.search.textChanged.connect(self.filter_items)
        header.addWidget(self.search)
        layout.addLayout(header)
        
        # Refresh Button
        self.refresh_btn = QPushButton("Načíst nainstalované aplikace")
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['accent']}; color: white; border: none;
                padding: 10px 20px; border-radius: 4px; font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {COLORS['accent_hover']}; }}
            QPushButton:disabled {{ background-color: {COLORS['input_bg']}; color: {COLORS['sub_text']}; }}
        """)
        self.refresh_btn.clicked.connect(self.load_apps)
        layout.addWidget(self.refresh_btn)
        
        # List Widget
        self.list_widget = QListWidget()
        self.list_widget.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.list_widget.setStyleSheet(f"""
            QListWidget {{ 
                background-color: {COLORS['bg_sidebar']}; 
                border: 1px solid {COLORS['border']};
                border-radius: 6px; 
                outline: none;
            }}
            QListWidget::item {{
                background-color: transparent;
                border-bottom: 1px solid {COLORS['border']};
                padding: 0px;
            }}
            QListWidget::item:hover {{
                background-color: {COLORS['item_hover']};
            }}
            QListWidget::item:selected {{
                background-color: transparent;
            }}
            QScrollBar:vertical {{
                border: none; background-color: {COLORS['bg_sidebar']}; width: 8px; margin: 0px; border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background-color: #444; min-height: 20px; border-radius: 4px;
            }}
            QScrollBar::handle:vertical:hover {{ background-color: {COLORS['accent']}; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; background: none; }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
        """)
        layout.addWidget(self.list_widget)
        
        # Status
        self.status = QLabel("Připraveno.")
        self.status.setStyleSheet(f"color: {COLORS['sub_text']};")
        layout.addWidget(self.status)

        self.all_items = [] 
        self.registry_cache = {} # Cache pro cesty k ikonám

    def load_apps(self):
        self.list_widget.clear()
        self.all_items = []
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText("Skenuji systém...")
        self.status.setText("Skenuji registry a Winget...")
        
        # 1. Nejprve na pozadí naskenujeme registry pro ikonky (je to rychlé)
        # Děláme to v hlavním vlákně před spuštěním wingetu, nebo bychom mohli také ve vlákně
        try:
            self.registry_cache = scan_registry_for_icons()
        except Exception as e:
            print(f"Chyba registru: {e}")
            self.registry_cache = {}

        # 2. Spustíme Winget scan
        self.worker = WingetListWorker()
        self.worker.finished.connect(self.on_loaded)
        self.worker.error.connect(lambda e: self.status.setText(f"Chyba: {e}"))
        self.worker.start()

    def on_loaded(self, apps):
        self.list_widget.setUpdatesEnabled(False)
        
        for app in apps:
            item = QListWidgetItem(self.list_widget)
            item.setSizeHint(QSize(0, 56))
            
            # Předáváme self.registry_cache do widgetu
            widget = AppItemWidget(app['name'], app['id'], self, self.registry_cache)
            self.list_widget.setItemWidget(item, widget)
            
            self.all_items.append((item, widget, app['name'].lower()))
            
        self.list_widget.setUpdatesEnabled(True)
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("Načíst nainstalované aplikace")
        self.status.setText(f"Nalezeno {len(apps)} aplikací.")

    def filter_items(self, text):
        text = text.lower()
        for item, widget, name in self.all_items:
            item.setHidden(text not in name)

    def confirm_uninstall(self, app_id):
        msg = QMessageBox(self)
        msg.setWindowTitle("Potvrzení odinstalace")
        msg.setText(f"Opravdu chcete odinstalovat tuto aplikaci?\n\nID: {app_id}")
        msg.setIcon(QMessageBox.Icon.Warning)
        
        btn_yes = msg.addButton("Ano, odinstalovat", QMessageBox.ButtonRole.YesRole)
        msg.addButton("Zrušit", QMessageBox.ButtonRole.NoRole)
        
        msg.setStyleSheet(f"background-color: {COLORS['bg_main']}; color: {COLORS['fg']};")
        msg.exec()
        
        if msg.clickedButton() == btn_yes:
            self.start_uninstall(app_id)

    def start_uninstall(self, app_id):
        self.status.setText(f"Odinstalovávám {app_id}...")
        self.u_worker = UninstallWorker(app_id)
        self.u_worker.log.connect(lambda s: self.status.setText(s))
        self.u_worker.finished.connect(lambda: [self.status.setText("Hotovo."), self.load_apps()])
        self.u_worker.start()