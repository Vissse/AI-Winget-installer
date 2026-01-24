import json
import re
import subprocess
import os
import requests
import difflib
from urllib.parse import urlparse
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QListWidget, QListWidgetItem, QLineEdit, 
                             QProgressBar, QMessageBox, QMenu, QCheckBox, QFrame,
                             QDialog, QTabWidget, QComboBox, QFileDialog, QDialogButtonBox)
from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal
from PyQt6.QtGui import QIcon, QAction, QPixmap, QImage, QPainter, QColor

from config import COLORS
from settings_manager import SettingsManager
from google import genai 
from config import resource_path

# Import presetu
try:
    from presets import PRESETS
except ImportError:
    PRESETS = {}

# --- TŘÍDA PRO TLAČÍTKA S DYNAMICKÝM PŘEBARVENÍM IKONY ---

class HoverButton(QPushButton):
    """Tlačítko, které při najetí myší softwarově přebarví ikonku i text."""
    def __init__(self, text, icon_path, style_template, parent=None):
        super().__init__(text, parent)
        self.icon_path = resource_path(icon_path)
        self.style_template = style_template
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.set_colored_icon(False)

    def set_colored_icon(self, is_hover):
        if not os.path.exists(self.icon_path):
            return

        pixmap = QPixmap(self.icon_path)
        current_color = QColor(COLORS['accent']) if is_hover else QColor(
            COLORS['sub_text'] if "sub_text" in self.style_template else COLORS['fg']
        )

        colored_pixmap = QPixmap(pixmap.size())
        colored_pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(colored_pixmap)
        painter.drawPixmap(0, 0, pixmap)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        painter.fillRect(colored_pixmap.rect(), current_color)
        painter.end()

        self.setIcon(QIcon(colored_pixmap))
        
        self.setStyleSheet(f"""
            QPushButton {{
                background: transparent; border: none; outline: none;
                color: {current_color.name()}; font-weight: bold; font-size: 10pt;
                padding: 5px; text-align: left;
            }}
        """)

    def enterEvent(self, event):
        self.set_colored_icon(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.set_colored_icon(False)
        super().leaveEvent(event)

# --- POMOCNÉ TŘÍDY (WORKERS) ---

class IconWorker(QThread):
    loaded = pyqtSignal(QPixmap)

    def __init__(self, app_id, website=None, preset_url=None):
        super().__init__()
        self.app_id = app_id
        self.website = website
        self.preset_url = preset_url

    def get_domain(self, url):
        try:
            if not url.startswith("http"):
                url = "https://" + url
            return urlparse(url).netloc
        except:
            return ""

    def run(self):
        if self.preset_url:
            if self._try_load_url(self.preset_url): return

        if self.app_id:
            clean_id = self.app_id
            lower_id = self.app_id.lower()
            dashed_id = lower_id.replace(".", "-")
            
            base_dash = "https://cdn.jsdelivr.net/gh/walkxcode/dashboard-icons/png"
            if self._try_load_url(f"{base_dash}/{dashed_id}.png"): return
            if self._try_load_url(f"{base_dash}/{lower_id}.png"): return
            
            base_uniget = "https://raw.githubusercontent.com/marticliment/UnigetUI/main/src/UnigetUI.PackageEngine/Assets/Packages"
            if self._try_load_url(f"{base_uniget}/{clean_id}.png"): return
            if self._try_load_url(f"{base_uniget}/{lower_id}.png"): return

        if self.website:
            domain = self.get_domain(self.website)
            if domain:
                if self._try_load_url(f"https://icons.duckduckgo.com/ip3/{domain}.ico"): return
                if self._try_load_url(f"https://www.google.com/s2/favicons?domain={domain}&sz=64"): return

    def _try_load_url(self, url):
        try:
            session = requests.Session()
            session.headers.update({'User-Agent': 'Mozilla/5.0'})
            response = session.get(url, timeout=1.5, stream=True)
            if response.status_code == 200:
                data = response.content
                if len(data) > 50:
                    image = QImage()
                    image.loadFromData(data)
                    if not image.isNull():
                        pixmap = QPixmap.fromImage(image)
                        pixmap = pixmap.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                        self.loaded.emit(pixmap)
                        return True
        except Exception:
            pass
        return False

class SearchWorker(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, query, use_smart_search=True):
        super().__init__()
        self.query = query
        self.use_smart_search = use_smart_search

    def run(self):
        if not self.use_smart_search:
            try:
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                cmd = f'winget search "{self.query}" --accept-source-agreements'
                result = subprocess.run(cmd, capture_output=True, text=True, startupinfo=startupinfo, encoding='cp852', errors='replace')
                
                lines = result.stdout.split('\n')
                data = []
                header_found = False
                
                for line in lines:
                    if "Name" in line and "Id" in line:
                        header_found = True
                        continue
                    if not header_found or "---" in line or not line.strip():
                        continue
                        
                    parts = re.split(r'\s{2,}', line.strip())
                    if len(parts) >= 2:
                        name = parts[0]
                        app_id = parts[1]
                        version = parts[2] if len(parts) > 2 else "Unknown"
                        
                        data.append({
                            "name": name,
                            "id": app_id,
                            "version": version,
                            "website": "" 
                        })
                
                self.finished.emit(data)
                return
            except Exception as e:
                self.error.emit(f"Chyba Winget hledání: {str(e)}")
                return

        try:
            settings = SettingsManager.load_settings()
            api_key = settings.get("api_key", "")
        except Exception:
            self.error.emit("Nepodařilo se načíst nastavení.")
            return

        preset_keys = list(PRESETS.keys())
        query_lower = self.query.lower().strip()
        matched_preset_key = None

        if query_lower in preset_keys:
            matched_preset_key = query_lower
        if not matched_preset_key:
            candidates = [k for k in preset_keys if k.startswith(query_lower)]
            if len(candidates) == 1:
                matched_preset_key = candidates[0]
        if not matched_preset_key:
            matches = difflib.get_close_matches(query_lower, preset_keys, n=1, cutoff=0.8)
            if matches and abs(len(query_lower) - len(matches[0])) <= 3:
                matched_preset_key = matches[0]

        if matched_preset_key:
            data = PRESETS[matched_preset_key]
            while isinstance(data, str): data = PRESETS.get(data, [])
            if isinstance(data, list) and len(data) > 0:
                for item in data:
                    if 'version' not in item: item['version'] = "Latest (Preset)"
                self.finished.emit(data)
                return 

        if not api_key:
            self.error.emit("Nenalezeno v presetech a chybí API klíč.")
            return

        try:
            client = genai.Client(api_key=api_key)
        except Exception as e:
            self.error.emit(f"Chyba inicializace AI: {str(e)}")
            return

        intent_prompt = f"""
        Jsi expert na Windows software a Winget repozitář.
        Uživatel zadal: "{self.query}"
        Pokud hledá konkrétní app, vrať jen opravený název.
        Pokud hledá kategorii, vrať seznam nejlepších aplikací.
        Odpověz POUZE ve formátu: QUERIES: app1;app2;app3
        """
        search_terms = []
        try:
            response = client.models.generate_content(model="gemini-2.0-flash", contents=intent_prompt)
            raw_intent = response.text.strip()
            if "QUERIES:" in raw_intent:
                clean_line = raw_intent.replace("QUERIES:", "").strip()
                search_terms = [t.strip() for t in clean_line.split(";") if t.strip()]
            else:
                search_terms = [self.query]
        except Exception:
            search_terms = [self.query]

        combined_output = ""
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        for term in search_terms:
            try:
                cmd = f'winget search "{term}" --source winget --accept-source-agreements -n 3'
                result = subprocess.run(cmd, capture_output=True, text=True, startupinfo=startupinfo, encoding='cp852', errors='replace')
                combined_output += f"\n--- VÝSLEDKY PRO '{term}' ---\n" + result.stdout
            except Exception: pass

        filter_prompt = f"""
        Mám výstup z příkazové řádky (Winget Search) pro různé hledané výrazy.
        Původní dotaz uživatele byl: "{self.query}"
        SUROVÁ DATA Z WINGET:
        '''{combined_output}'''
        INSTRUKCE:
        1. Analyzuj data a najdi aplikace odpovídající záměru.
        2. Ignoruj balast, bety, knihovny.
        3. Extrahuj Název, ID a Verzi.
        VÝSTUPNÍ FORMÁT (čistý JSON pole):
        [ {{ "name": "Název", "id": "Přesné.ID", "version": "verze", "website": "domena.com" }} ]
        """
        try:
            response = client.models.generate_content(model="gemini-2.0-flash", contents=filter_prompt)
            raw_text = response.text
            json_str = raw_text.replace("```json", "").replace("```", "").strip()
            match = re.search(r'\[.*\]', json_str, re.DOTALL)
            data = json.loads(match.group(0)) if match else []
            for item in data:
                if not item.get('version') or item['version'] == "Latest": 
                    item['version'] = "Latest/Unknown"
            self.finished.emit(data)
        except Exception as e:
            self.error.emit(f"Chyba zpracování výsledků: {str(e)}")

# --- DIALOG ---
class InstallationOptionsDialog(QDialog):
    def __init__(self, parent=None, current_options=None):
        super().__init__(parent)
        self.setWindowTitle("Možnosti instalace")
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
        self.setStyleSheet(f"""
            QDialog {{ background-color: {COLORS['bg_main']}; color: {COLORS['fg']}; }}
            QTabWidget::pane {{ border: 1px solid {COLORS['border']}; }}
            QTabBar::tab {{ background: {COLORS['bg_sidebar']}; color: {COLORS['sub_text']}; padding: 8px 15px; margin-right: 2px; }}
            QTabBar::tab:selected {{ background: {COLORS['item_bg']}; color: {COLORS['fg']}; border-top: 2px solid {COLORS['accent']}; }}
            QLabel {{ color: {COLORS['fg']}; font-size: 10pt; }}
            QCheckBox {{ color: {COLORS['fg']}; font-size: 10pt; spacing: 8px; }}
            QCheckBox::indicator {{ width: 18px; height: 18px; border: 1px solid {COLORS['border']}; border-radius: 4px; }}
            QCheckBox::indicator:checked {{ background-color: {COLORS['accent']}; border-color: {COLORS['accent']}; image: url(check.png); }}
            QComboBox {{ background: {COLORS['input_bg']}; border: 1px solid {COLORS['border']}; padding: 5px; color: {COLORS['fg']}; border-radius: 4px; }}
            QLineEdit {{ background: {COLORS['input_bg']}; border: 1px solid {COLORS['border']}; padding: 5px; color: {COLORS['fg']}; border-radius: 4px; }}
        """)
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        tab_general = QWidget()
        layout_gen = QVBoxLayout(tab_general)
        layout_gen.setContentsMargins(20, 20, 20, 20)
        layout_gen.setSpacing(15)
        self.chk_admin = QCheckBox("Spustit jako správce")
        self.chk_interactive = QCheckBox("Interaktivní instalace")
        self.chk_hash = QCheckBox("Přeskočit kontrolní součet")
        layout_gen.addWidget(self.chk_admin)
        layout_gen.addWidget(self.chk_interactive)
        layout_gen.addWidget(self.chk_hash)
        layout_gen.addSpacing(10)
        line = QFrame(); line.setFrameShape(QFrame.Shape.HLine); line.setStyleSheet(f"color: {COLORS['border']};")
        layout_gen.addWidget(line)
        layout_gen.addSpacing(10)
        lbl_ver = QLabel("Verze:")
        self.combo_version = QComboBox()
        self.combo_version.addItems(["Poslední (Latest)", "Zeptat se při instalaci"])
        layout_gen.addWidget(lbl_ver)
        layout_gen.addWidget(self.combo_version)
        self.chk_ignore_updates = QCheckBox("Ignorovat budoucí aktualizace tohoto balíčku")
        layout_gen.addWidget(self.chk_ignore_updates)
        layout_gen.addStretch()
        self.tabs.addTab(tab_general, "Obecné / Verze")

        tab_arch = QWidget()
        layout_arch = QVBoxLayout(tab_arch)
        layout_arch.setContentsMargins(20, 20, 20, 20)
        layout_arch.setSpacing(15)
        lbl_arch = QLabel("Architektura:")
        self.combo_arch = QComboBox()
        self.combo_arch.addItems(["Výchozí", "x64", "x86", "arm64"])
        layout_arch.addWidget(lbl_arch)
        layout_arch.addWidget(self.combo_arch)
        lbl_scope = QLabel("Rozsah instalace:")
        self.combo_scope = QComboBox()
        self.combo_scope.addItems(["Výchozí (User/Machine)", "User (Pouze pro mě)", "Machine (Pro všechny)"])
        layout_arch.addWidget(lbl_scope)
        layout_arch.addWidget(self.combo_scope)
        lbl_path = QLabel("Umístění instalace:")
        path_layout = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Nenastaveno nebo neznámo (Výchozí)")
        btn_path = QPushButton("Vybrat")
        btn_path.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_path.clicked.connect(self.select_path)
        btn_path.setStyleSheet(f"background: {COLORS['item_bg']}; color: {COLORS['accent']}; border: none; font-weight: bold;")
        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(btn_path)
        layout_arch.addWidget(lbl_path)
        layout_arch.addLayout(path_layout)
        layout_arch.addStretch()
        self.tabs.addTab(tab_arch, "Architektura a umístění")

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        if current_options:
            self.chk_admin.setChecked(current_options.get("admin", False))
            self.chk_interactive.setChecked(current_options.get("interactive", False))
            self.chk_hash.setChecked(current_options.get("hash", False))
            self.combo_arch.setCurrentText(current_options.get("arch", "Výchozí"))
            self.path_edit.setText(current_options.get("path", ""))

    def select_path(self):
        d = QFileDialog.getExistingDirectory(self, "Vybrat složku pro instalaci")
        if d: self.path_edit.setText(d)

    def get_options(self):
        return {
            "admin": self.chk_admin.isChecked(),
            "interactive": self.chk_interactive.isChecked(),
            "hash": self.chk_hash.isChecked(),
            "version": self.combo_version.currentText(),
            "arch": self.combo_arch.currentText(),
            "scope": self.combo_scope.currentText(),
            "path": self.path_edit.text()
        }

# --- TABULKOVÝ ŘÁDEK (WIDGET) ---

class AppTableWidget(QWidget):
    def __init__(self, data, parent_controller, queue_page_ref):
        super().__init__()
        self.data = data
        self.controller = parent_controller
        self.queue_page = queue_page_ref
        self.current_pixmap = None

        self.setStyleSheet("background-color: transparent; font-size: 10pt;")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5) 
        layout.setSpacing(15)
        
        self.chk = QCheckBox()
        self.chk.setFixedWidth(30)
        self.chk.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chk.setStyleSheet(f"""
            QCheckBox::indicator {{ width: 18px; height: 18px; border: 1px solid {COLORS['sub_text']}; border-radius: 4px; background: transparent; }}
            QCheckBox::indicator:checked {{ background-color: {COLORS['accent']}; border-color: {COLORS['accent']}; image: url(check.png); }} 
        """)
        
        if self.data['id'] in self.queue_page.queue_data:
            self.chk.setChecked(True)
        self.chk.stateChanged.connect(self.toggle_queue)
        layout.addWidget(self.chk)

        self.icon_lbl = QLabel()
        self.icon_lbl.setFixedSize(24, 24)
        
        default_icon_path = resource_path(os.path.join("images", "package-thin.png"))
        if os.path.exists(default_icon_path):
            pix = QPixmap(default_icon_path)
            pix = pix.scaled(24, 24, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.icon_lbl.setPixmap(pix)
        else:
            self.icon_lbl.setText("📦") 
            self.icon_lbl.setStyleSheet("font-size: 12pt; color: #888; border: none; background: transparent;")
        
        self.icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.icon_lbl)

        self.icon_worker = IconWorker(data.get('id'), data.get('website'), data.get('icon_url'))
        self.icon_worker.loaded.connect(self.set_icon)
        self.icon_worker.start()

        name_lbl = QLabel(data['name'])
        name_lbl.setStyleSheet("font-weight: bold; color: white; background: transparent;")
        layout.addWidget(name_lbl, stretch=4)

        id_lbl = QLabel(data['id'])
        id_lbl.setStyleSheet(f"color: {COLORS['sub_text']}; background: transparent;")
        layout.addWidget(id_lbl, stretch=3)

        ver_lbl = QLabel(data.get('version', 'Unknown'))
        ver_lbl.setFixedWidth(100)
        ver_lbl.setStyleSheet(f"color: {COLORS['sub_text']}; background: transparent;")
        layout.addWidget(ver_lbl)

        src_lbl = QLabel("Winget")
        src_lbl.setFixedWidth(80)
        src_lbl.setStyleSheet(f"color: {COLORS['sub_text']}; background: transparent;")
        layout.addWidget(src_lbl)

    def set_icon(self, pixmap):
        self.current_pixmap = pixmap
        scaled = pixmap.scaled(24, 24, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.icon_lbl.setPixmap(scaled)
        self.icon_lbl.setText("")

    def toggle_queue(self, state):
        if state == 2:
            self.queue_page.add_to_queue(self.data, self.current_pixmap)
        else:
            self.queue_page.remove_item_by_id(self.data['id'])

# --- HLAVNÍ UI (InstallerPage) ---

class InstallerPage(QWidget):
    def __init__(self, queue_page_ref):
        super().__init__()
        self.queue_page = queue_page_ref
        self.smart_search_active = True
        self.installation_options = {}
        self._is_ai_hovered = False

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # === A. HORNÍ VYHLEDÁVACÍ LIŠTA ===
        top_bar = QWidget()
        top_bar.setStyleSheet(f"background-color: {COLORS['bg_main']}; border-bottom: 1px solid {COLORS['border']};")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(20, 15, 20, 15)
        
        lbl_title = QLabel("Hledat balíčky")
        lbl_title.setStyleSheet("font-size: 14pt; font-weight: bold; color: white; border: none; outline: none;")
        top_layout.addWidget(lbl_title)
        top_layout.addSpacing(20)

        # FIX: Container pro vyhledávání s PEVNOU ŠÍŘKOU
        self.search_container = QFrame()
        self.search_container.setFixedWidth(700) # Fixní délka
        self.search_container.setFixedHeight(38)
        self.search_container.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['input_bg']}; 
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
            }}
            QFrame:focus-within {{
                border: 1px solid {COLORS['accent']};
            }}
        """)
        search_cont_layout = QHBoxLayout(self.search_container)
        search_cont_layout.setContentsMargins(10, 0, 5, 0)
        search_cont_layout.setSpacing(0)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Zadejte záměr (např. 'střih videa')...")
        self.search_input.setStyleSheet("border: none; background: transparent; color: white; font-size: 10pt;")
        self.search_input.returnPressed.connect(self.start_search)
        
        self.btn_search = HoverButton("", "images/magnifying-glass-thin.png", "fg")
        self.btn_search.setFixedSize(32, 32)
        self.btn_search.setIconSize(QSize(18, 18))
        self.btn_search.clicked.connect(self.start_search)
        self.btn_search.setStyleSheet("background: transparent; border: none; padding: 0;")

        search_cont_layout.addWidget(self.search_input)
        search_cont_layout.addWidget(self.btn_search)
        top_layout.addWidget(self.search_container) # Odebrán stretch faktor

        # Tlačítko Smart Search
        self.btn_toggle_ai = QPushButton()
        self.btn_toggle_ai.setFixedHeight(36)
        self.btn_toggle_ai.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_ai.setIconSize(QSize(20, 20))
        self.btn_toggle_ai.setToolTip("Smart Search: Používá AI k nalezení softwaru.")
        
        self.btn_toggle_ai.enterEvent = self._ai_btn_enter
        self.btn_toggle_ai.leaveEvent = self._ai_btn_leave
        
        self.update_toggle_icon()
        self.btn_toggle_ai.clicked.connect(self.toggle_smart_search)
        top_layout.addWidget(self.btn_toggle_ai)

        top_layout.addStretch() # Přidán stretch až na konec barové lišty

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
        action_layout.setSpacing(10)

        split_container = QFrame()
        split_container.setFixedHeight(34)
        split_container.setStyleSheet(f"QFrame {{ background-color: {COLORS['item_bg']}; border: 1px solid {COLORS['border']}; border-radius: 6px; }} QFrame:hover {{ border-color: {COLORS['accent']}; }}")
        split_layout = QHBoxLayout(split_container)
        split_layout.setContentsMargins(0, 0, 0, 0)
        split_layout.setSpacing(0)

        self.btn_install_selection = QPushButton("  Nainstalovat vybrané")
        self.btn_install_selection.setIcon(QIcon(resource_path("images/download-simple-thin.png")))
        self.btn_install_selection.setFixedHeight(32)
        self.btn_install_selection.setStyleSheet(f"QPushButton {{ background: transparent; border: none; color: white; padding: 0 15px; font-weight: bold; font-size: 10pt; border-top-left-radius: 5px; border-bottom-left-radius: 5px; border-top-right-radius: 0px; border-bottom-right-radius: 0px; }} QPushButton:hover {{ background-color: {COLORS['item_hover']}; }}")
        self.btn_install_selection.clicked.connect(self.run_install_from_bar)

        mid_line = QFrame()
        mid_line.setFixedWidth(1)
        mid_line.setStyleSheet(f"background-color: {COLORS['border']}; border: none;")

        self.btn_settings_quick = QPushButton()
        self.btn_settings_quick.setFixedSize(32, 32)
        self.btn_settings_quick.setIcon(self.get_colored_icon_for_split("images/gear-six-thin.png", COLORS['fg']))
        self.btn_settings_quick.setIconSize(QSize(18, 18))
        self.btn_settings_quick.setStyleSheet(f"QPushButton {{ background: transparent; border: none; border-top-right-radius: 5px; border-bottom-right-radius: 5px; border-top-left-radius: 0px; border-bottom-left-radius: 0px; }} QPushButton:hover {{ background-color: {COLORS['item_hover']}; }}")
        self.btn_settings_quick.clicked.connect(self.open_options_dialog)

        split_layout.addWidget(self.btn_install_selection)
        split_layout.addWidget(mid_line)
        split_layout.addWidget(self.btn_settings_quick)
        action_layout.addWidget(split_container)
        
        action_layout.addStretch()

        self.btn_help = HoverButton(" Nápověda", "images/question-thin.png", "sub_text")
        self.btn_help.setIconSize(QSize(20, 20))
        self.btn_help.clicked.connect(self.show_help)
        action_layout.addWidget(self.btn_help)
        
        main_layout.addWidget(action_bar)

        # === C. TABULKA VÝSLEDKŮ ===
        header_widget = QWidget()
        header_widget.setStyleSheet(f"background-color: {COLORS['bg_sidebar']}; border: none; font-size: 9pt;")
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(35, 8, 35, 8) 
        header_layout.setSpacing(15)

        h_headers = [("", 30), ("", 24), ("NÁZEV BALÍČKU", 0), ("ID BALÍČKU", 0), ("VERZE", 100), ("ZDROJ", 80)]
        for i, (text, width) in enumerate(h_headers):
            lbl = QLabel(text)
            lbl.setStyleSheet("font-weight: bold; color: white; border: none;")
            if width > 0: lbl.setFixedWidth(width)
            stretch = 4 if i == 2 else (3 if i == 3 else 0)
            header_layout.addWidget(lbl, stretch=stretch)
        main_layout.addWidget(header_widget)

        self.results_list = QListWidget()
        self.results_list.setStyleSheet(f"QListWidget {{ background-color: {COLORS['bg_main']}; border: none; padding: 0 30px; }} QListWidget::item {{ border-bottom: 1px solid {COLORS['border']}; padding: 0px; }} QListWidget::item:hover {{ background-color: {COLORS['item_hover']}; }}")
        self.results_list.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        main_layout.addWidget(self.results_list)

    # --- POMOCNÉ FUNKCE ---

    def _ai_btn_enter(self, event):
        self._is_ai_hovered = True
        self.update_toggle_icon()
        super(QPushButton, self.btn_toggle_ai).enterEvent(event)

    def _ai_btn_leave(self, event):
        self._is_ai_hovered = False
        self.update_toggle_icon()
        super(QPushButton, self.btn_toggle_ai).leaveEvent(event)

    def update_toggle_icon(self):
        icon_path = resource_path("images/sparkle-fill.png") if self.smart_search_active else resource_path("images/sparkle-thin.png")
        
        if self.smart_search_active:
            self.btn_toggle_ai.setText(" SMART")
            self.btn_toggle_ai.setFixedWidth(90)
        else:
            self.btn_toggle_ai.setText("")
            self.btn_toggle_ai.setFixedWidth(40) # Hover funguje jen na ikonu
            
        color = COLORS['accent'] if (self.smart_search_active or self._is_ai_hovered) else COLORS['fg']
        
        if os.path.exists(icon_path):
            pixmap = QPixmap(icon_path)
            colored_pixmap = QPixmap(pixmap.size()); colored_pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(colored_pixmap); painter.drawPixmap(0, 0, pixmap)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
            painter.fillRect(colored_pixmap.rect(), QColor(color)); painter.end()
            self.btn_toggle_ai.setIcon(QIcon(colored_pixmap))
        
        self.btn_toggle_ai.setStyleSheet(f"QPushButton {{ background: transparent; border: none; color: {color}; font-weight: bold; font-size: 9pt; outline: none; padding: 5px; text-align: left; padding-left: 10px; }}")

    def get_colored_icon_for_split(self, path, color_hex):
        full_path = resource_path(path)
        if not os.path.exists(full_path): return QIcon()
        pixmap = QPixmap(full_path)
        colored = QPixmap(pixmap.size()); colored.fill(Qt.GlobalColor.transparent)
        p = QPainter(colored); p.drawPixmap(0, 0, pixmap); p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn); p.fillRect(colored.rect(), QColor(color_hex)); p.end()
        return QIcon(colored)

    def toggle_smart_search(self):
        self.smart_search_active = not self.smart_search_active
        self.update_toggle_icon()
        self.search_input.setPlaceholderText("Zadejte záměr..." if self.smart_search_active else "Zadejte přesný název...")

    def run_install_from_bar(self):
        if not self.queue_page.queue_data:
            QMessageBox.warning(self, "Prázdná fronta", "Vyberte nejprve balíčky.")
            return
        self.queue_page.run_installation()

    def open_options_dialog(self):
        dlg = InstallationOptionsDialog(self, self.installation_options)
        if dlg.exec(): self.installation_options = dlg.get_options()

    def show_help(self):
        QMessageBox.information(self, "Nápověda", "SMART: Používá AI k pochopení záměru.\nKLASIK: Standardní Winget hledání.")

    def start_search(self):
        query = self.search_input.text().strip()
        if not query: return
        self.results_list.clear(); self.btn_search.setEnabled(False); self.progress.setRange(0, 0); self.progress.show()
        self.worker = SearchWorker(query, use_smart_search=self.smart_search_active)
        self.worker.finished.connect(self.on_search_finished); self.worker.error.connect(self.on_search_error); self.worker.start()

    def on_search_finished(self, results):
        self.progress.hide(); self.btn_search.setEnabled(True)
        if not results: self.show_empty_state("Nic nenalezeno."); return
        for app in results:
            item = QListWidgetItem(self.results_list); item.setSizeHint(QSize(0, 50))
            widget = AppTableWidget(app, self, self.queue_page); self.results_list.setItemWidget(item, widget)

    def on_search_error(self, err_msg):
        self.progress.hide(); self.btn_search.setEnabled(True); self.show_empty_state(f"Chyba: {err_msg}")

    def show_empty_state(self, message):
        item = QListWidgetItem(self.results_list); item.setFlags(Qt.ItemFlag.NoItemFlags); widget = QLabel(message); widget.setAlignment(Qt.AlignmentFlag.AlignCenter); widget.setStyleSheet("color: #888; padding: 40px; font-size: 10pt;"); item.setSizeHint(QSize(0, 100)); self.results_list.setItemWidget(item, widget)

    def refresh_checkboxes(self):
        for i in range(self.results_list.count()):
            item = self.results_list.item(i); widget = self.results_list.itemWidget(item)
            if isinstance(widget, AppTableWidget):
                widget.chk.blockSignals(True); widget.chk.setChecked(widget.data['id'] in self.queue_page.queue_data); widget.chk.blockSignals(False)