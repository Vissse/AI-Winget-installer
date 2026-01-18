import json
import re
import subprocess
import os
import requests
import webbrowser
import difflib
from urllib.parse import urlparse
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QListWidget, QListWidgetItem, QLineEdit, 
                             QProgressBar, QMessageBox, QFileDialog, QToolTip)
from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal, QEvent, QObject
from PyQt6.QtGui import QIcon, QColor, QFont, QCursor, QPixmap, QImage

from config import COLORS, OUTPUT_FILE
from settings_manager import SettingsManager
from google import genai 
from install_manager import InstallationDialog

# Import presetu
try:
    from presets import PRESETS
except ImportError:
    PRESETS = {}

# --- 0. POMOCNÉ TŘÍDY ---

class InstantTooltip(QObject):
    def eventFilter(self, widget, event):
        if event.type() == QEvent.Type.ToolTip:
            if widget.toolTip():
                QToolTip.showText(QCursor.pos(), widget.toolTip())
            return True 
        return False

import json
import re
import subprocess
import os
import requests
import webbrowser
from urllib.parse import urlparse
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QListWidget, QListWidgetItem, QLineEdit, 
                             QProgressBar, QMessageBox, QFileDialog, QToolTip)
from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal, QEvent, QObject
from PyQt6.QtGui import QIcon, QColor, QFont, QCursor, QPixmap, QImage

from config import COLORS, OUTPUT_FILE
from settings_manager import SettingsManager
from google import genai 

try:
    from presets import PRESETS
except ImportError:
    PRESETS = {}

# --- 0. POMOCNÉ TŘÍDY ---

class InstantTooltip(QObject):
    def eventFilter(self, widget, event):
        if event.type() == QEvent.Type.ToolTip:
            if widget.toolTip():
                QToolTip.showText(QCursor.pos(), widget.toolTip())
            return True 
        return False

class IconWorker(QThread):
    loaded = pyqtSignal(QPixmap)

    # PŘIDÁN PARAMETR: preset_url=None
    def __init__(self, app_id, website=None, preset_url=None):
        super().__init__()
        self.app_id = app_id
        self.website = website
        self.preset_url = preset_url

    def get_domain(self, url):
        try:
            return urlparse(url).netloc
        except:
            return ""

    def run(self):
        # 1. PRIORITA: Pokud máme ikonku přímo v presetu, použijeme ji!
        session = requests.Session()
        session.headers.update({'User-Agent': 'Mozilla/5.0'})

        if self.preset_url:
            try:
                response = session.get(self.preset_url, timeout=3)
                if response.status_code == 200:
                    image = QImage()
                    image.loadFromData(response.content)
                    if not image.isNull():
                        pixmap = QPixmap.fromImage(image)
                        pixmap = pixmap.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                        self.loaded.emit(pixmap)
                        return # Hotovo, končíme
            except:
                pass # Pokud selže preset, pokračujeme dál

        if not self.app_id: return

        # ... (zbytek metody run zůstává stejný: Winget API, GitHub, Favicons) ...
        urls_to_try = []
        
        # --- 1. ZLATÝ STANDARD: WINGET.RUN API ---
        # ... kód pokračuje ...

        # --- 1. ZLATÝ STANDARD: WINGET.RUN API ---
        # Toto je nejspolehlivější metoda. API nám vrátí přesnou URL ikony definovanou v manifestu.
        try:
            api_url = f"https://api.winget.run/v2/packages/{self.app_id}"
            # Voláme API (krátký timeout, ať neblokujeme, pokud server neodpovídá)
            api_resp = session.get(api_url, timeout=2.5)
            if api_resp.status_code == 200:
                data = api_resp.json()
                # Cesta k ikoně v JSONu
                icon_url = data.get("Package", {}).get("Latest", {}).get("IconUrl")
                if icon_url:
                    urls_to_try.append(icon_url)
        except:
            pass

        # --- 2. PŘÍPRAVA ID VARIANT PRO REPOZITÁŘE ---
        clean_id = self.app_id
        lower_id = self.app_id.lower()
        # Pokud ID obsahuje tečky, zkusíme variantu s pomlčkami (časté u dashboard-icons)
        dashed_id = lower_id.replace(".", "-")
        
        # Zkrácené ID (např. 'krita' z 'KDE.Krita')
        short_id = self.app_id.split(".")[-1] if "." in self.app_id else self.app_id
        short_lower = short_id.lower()

        # --- 3. GITHUB REPOZITÁŘE (FALLBACK) ---
        
        # A) UnigetUI (Dříve WingetUI) - Velká databáze
        base_uniget = "https://raw.githubusercontent.com/marticliment/UnigetUI/main/src/UnigetUI.PackageEngine/Assets/Packages"
        urls_to_try.append(f"{base_uniget}/{clean_id}.png")
        urls_to_try.append(f"{base_uniget}/{lower_id}.png")
        urls_to_try.append(f"{base_uniget}/{short_id}.png")

        # B) Dashboard Icons (Walkxcode) - Kvalitní loga, často používají pomlčky místo teček
        base_dash = "https://cdn.jsdelivr.net/gh/walkxcode/dashboard-icons/png"
        urls_to_try.append(f"{base_dash}/{dashed_id}.png")      # např. google-chrome.png
        urls_to_try.append(f"{base_dash}/{lower_id}.png")       # např. discord.discord.png
        urls_to_try.append(f"{base_dash}/{short_lower}.png")    # např. krita.png

        # --- 4. WEBOVÉ FAVICONY (POSLEDNÍ ZÁCHRANA) ---
        if self.website and "http" in self.website:
            domain = self.get_domain(self.website)
            if domain:
                # DuckDuckGo (často najde i to, co Google ne)
                urls_to_try.append(f"https://icons.duckduckgo.com/ip3/{domain}.ico")
                # Google
                urls_to_try.append(f"https://www.google.com/s2/favicons?domain={domain}&sz=64")

        # --- 5. STAHOVÁNÍ ---
        for url in urls_to_try:
            try:
                response = session.get(url, timeout=1.5)
                
                # Kontrola, zda jsme dostali validní obrázek (ne 404 stránku nebo prázdný soubor)
                if response.status_code == 200 and len(response.content) > 100:
                    image = QImage()
                    image.loadFromData(response.content)
                    
                    if not image.isNull():
                        # Převedeme na Pixmap a zmenšíme kvalitně na 32x32
                        pixmap = QPixmap.fromImage(image)
                        pixmap = pixmap.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                        self.loaded.emit(pixmap)
                        return # MÁME IKONU, KONEC
            except:
                continue

# --- 1. MOZEK VYHLEDÁVÁNÍ (SearchWorker) ---
class SearchWorker(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, query):
        super().__init__()
        self.query = query

    def run(self):
        settings = SettingsManager.load_settings()
        api_key = settings.get("api_key", "")
        
        # Načtení klíčů presetů pro matchování
        preset_keys = list(PRESETS.keys())
        query_lower = self.query.lower().strip()
        matched_preset_key = None

        # =================================================================
        # KROK 1: HEURISTIKA & FUZZY MATCHING (Lokální, 0ms)
        # =================================================================
        # Řeší překlepy: "progfozieč" -> "prohlížeč"
        
        # A) Přímá shoda
        if query_lower in preset_keys:
            matched_preset_key = query_lower
            
        # B) Fuzzy shoda (Levenshtein distance)
        # cutoff=0.6 znamená, že slovo musí být alespoň z 60 % podobné
        if not matched_preset_key:
            matches = difflib.get_close_matches(query_lower, preset_keys, n=1, cutoff=0.6)
            if matches:
                matched_preset_key = matches[0]
                print(f"[LOG] Fuzzy match nalezen: '{self.query}' -> '{matched_preset_key}'")

        # =================================================================
        # KROK 2: AI SEMANTICKÁ KLASIFIKACE (Cloud, ~500ms)
        # =================================================================
        # Řeší význam: "surfovat na webu" -> "prohlížeč"
        
        if not matched_preset_key and api_key:
            try:
                client = genai.Client(api_key=api_key)
                
                # Zjednodušený prompt pro klasifikaci
                classification_prompt = f"""
                Mám definované kategorie softwaru (PRESETS): {json.dumps(preset_keys)}.
                Uživatel hledá: "{self.query}".
                
                ÚKOL:
                Pokud záměr uživatele silně odpovídá některé z kategorií (např. 'surfovat' -> 'prohlížeč', 'psát dokumenty' -> 'office'), vrať POUZE název té kategorie.
                Pokud to neodpovídá žádnému presetu, vrať řetězec "NULL".
                
                Odpověz pouze jedním slovem (klíčem nebo NULL).
                """
                
                response = client.models.generate_content(
                    model="gemini-2.5-flash", 
                    contents=classification_prompt
                )
                
                ai_suggestion = response.text.strip().replace('"', '').replace("'", "")
                
                if ai_suggestion in preset_keys:
                    matched_preset_key = ai_suggestion
                    print(f"[LOG] AI Preset match: '{self.query}' -> '{matched_preset_key}'")

            except Exception as e:
                print(f"[WARN] AI Classification failed: {e}")
                # Pokračujeme dál, nekončíme chybou

        # =================================================================
        # KROK 3: VYZVEDNUTÍ DAT Z PRESETS (Pokud nalezeno v K1 nebo K2)
        # =================================================================
        
        if matched_preset_key:
            data = PRESETS[matched_preset_key]
            
            # Rekurzivní alias handling (např. "browser" -> "prohlížeč")
            while isinstance(data, str):
                data = PRESETS.get(data, [])

            if isinstance(data, list) and len(data) > 0:
                # Doplnění verze u statických presetů
                for item in data:
                    if 'version' not in item:
                        item['version'] = "Latest (Preset)"
                
                self.finished.emit(data)
                return 

        # =================================================================
        # KROK 4: WINGET SEARCH (Fallback pro specifické aplikace)
        # =================================================================
        # Pokud jsme doteď nenašli shodu, znamená to, že uživatel hledá
        # něco specifického, co není v presetech (např. "Blender").
        
        if not api_key:
            self.error.emit("Chybí API klíč a shoda v presetech nebyla nalezena.")
            return

        search_terms = []
        try:
            intent_prompt = f"""
            Jsi expert na Windows software. Uživatel hledá: "{self.query}"
            Vrať seznam přesných názvů pro 'winget search'.
            Odpověz POUZE ve formátu: QUERIES: app1;app2
            """
            response = client.models.generate_content(model="gemini-2.5-flash", contents=intent_prompt)
            
            if response.text and "QUERIES:" in response.text:
                clean_line = response.text.replace("QUERIES:", "").strip()
                search_terms = [t.strip() for t in clean_line.split(";") if t.strip()]
            else:
                search_terms = [self.query]
        except Exception as e:
            search_terms = [self.query]

        # --- WINGET EXECUTION ---
        combined_output = ""
        for term in search_terms:
            try:
                cmd = f'winget search "{term}" --source winget --accept-source-agreements -n 3'
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                result = subprocess.run(cmd, capture_output=True, text=True, startupinfo=startupinfo, encoding='cp852', errors='replace')
                combined_output += result.stdout
            except Exception as e:
                print(f"Chyba hledání '{term}': {e}")

        # --- AI PARSING & FILTERING ---
        try:
            filter_prompt = f"""
            Analyzuj Winget výstup pro dotaz: "{self.query}".
            
            DATA:
            '''{combined_output}'''

            1. Najdi relevantní aplikace (ignoruj drivery/libs).
            2. Vždy preferuj novější verze.
            3. Vrať JSON pole:
            [
                {{ "name": "App Name", "id": "App.ID", "version": "verze", "website": "url_odhad" }}
            ]
            """
            response = client.models.generate_content(model="gemini-2.5-flash", contents=filter_prompt)
            raw_text = response.text
            json_str = raw_text.replace("```json", "").replace("```", "").strip()
            
            # Regex pro extrakci JSON pole, pokud AI kecá okolo
            match = re.search(r'\[.*\]', json_str, re.DOTALL)
            data = json.loads(match.group(0)) if match else []

            for item in data:
                if not item.get('version') or item['version'] == "Latest": 
                    item['version'] = "Latest/Unknown"

            self.finished.emit(data)

        except Exception as e:
            self.error.emit(f"Chyba zpracování: {str(e)}")


# --- 2. VZHLED ŘÁDKU (Widget) ---
class AppRowWidget(QWidget):
    def __init__(self, data, mode, parent_controller, cached_icon=None):
        super().__init__()
        self.data = data
        self.mode = mode 
        self.controller = parent_controller
        self.tooltip_filter = InstantTooltip()
        
        self.current_pixmap = cached_icon 

        self.setStyleSheet("background-color: transparent;")

        # Hlavní layout
        layout = QHBoxLayout(self)
        
        # Zarovnání a mezery
        if mode == 'queue':
            layout.setContentsMargins(10, 5, 10, 5)
            layout.setSpacing(15)
            layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        else:
            layout.setContentsMargins(15, 10, 15, 10) 
            layout.setSpacing(15) 
        
        # 1. IKONA
        self.icon_lbl = QLabel()
        self.icon_lbl.setFixedSize(32, 32)
        self.icon_lbl.setText("📦") 
        self.icon_lbl.setStyleSheet("font-size: 24px; color: #888; border: none; background: transparent; font-family: 'Segoe UI Emoji';")
        self.icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.icon_lbl)

        # LOGIKA IKONY
        if cached_icon:
            self.set_icon(cached_icon)
        else:
            self.icon_worker = IconWorker(
                data.get('id'), 
                data.get('website'), 
                data.get('icon_url')
            )
            self.icon_worker.loaded.connect(self.set_icon)
            self.icon_worker.start()

        # 2. TEXTOVÁ ČÁST
        text_layout = QVBoxLayout()
        
        if mode == 'queue':
            text_layout.setSpacing(0)
            text_layout.setContentsMargins(0, 0, 0, 0)
            text_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        else:
            text_layout.setSpacing(2) 
        
        name_lbl = QLabel(data['name'])
        name_lbl.setStyleSheet("font-weight: bold; font-size: 14px; color: white; background: transparent; border: none;")
        text_layout.addWidget(name_lbl)
        
        # 3. METADATA (Jen pro výsledky hledání)
        if mode == 'result':
            meta_container = QWidget()
            meta_layout = QHBoxLayout(meta_container)
            meta_layout.setContentsMargins(0, 0, 0, 0)
            meta_layout.setSpacing(5)
            
            id_text = f"{data['id']}"
            id_lbl = QLabel(id_text)
            id_lbl.setStyleSheet("color: #888888; font-size: 11px; background: transparent;")
            meta_layout.addWidget(id_lbl)
            
            website = data.get('website')
            if website:
                sep_lbl = QLabel("|")
                sep_lbl.setStyleSheet("color: #888888; font-size: 11px; background: transparent;")
                meta_layout.addWidget(sep_lbl)
                
                web_lbl = QLabel(website)
                web_lbl.setStyleSheet("color: #888888; font-size: 11px; background: transparent;")
                web_lbl.setCursor(Qt.CursorShape.PointingHandCursor)
                
                def open_web(e): webbrowser.open(website)
                def hover_enter(e): web_lbl.setStyleSheet(f"color: {COLORS['accent']}; font-size: 11px; text-decoration: underline; background: transparent;")
                def hover_leave(e): web_lbl.setStyleSheet("color: #888888; font-size: 11px; background: transparent;")
                    
                web_lbl.mousePressEvent = open_web
                web_lbl.enterEvent = hover_enter
                web_lbl.leaveEvent = hover_leave
                meta_layout.addWidget(web_lbl)
                
            meta_layout.addStretch()
            text_layout.addWidget(meta_container)
        
        layout.addLayout(text_layout)
        layout.addStretch()
        
        # 4. TLAČÍTKO AKCE
        self.btn = QPushButton()
        # ZMĚNA: Větší a obdélníkovější tlačítko (nebo zaoblený čtverec)
        self.btn.setFixedSize(40, 34) 
        self.btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn.installEventFilter(self.tooltip_filter)
        
        if mode == 'result':
            # --- TLAČÍTKO PŘIDAT (+) ---
            if self.controller.is_in_queue(data['id']):
                self.set_checked_state()
            else:
                self.set_add_state()
            self.btn.clicked.connect(self.add_to_queue)
        else:
            # --- TLAČÍTKO ODEBRAT (X) - NOVÝ STYL ---
            self.btn.setFixedSize(30, 30)
            self.btn.setText("\uE8BB") # Stejný znak jako v HelpDialog
            self.btn.setToolTip("Odebrat z fronty")
            
            self.btn.setStyleSheet(f"""
                QPushButton {{ 
                    background-color: transparent; 
                    color: #777777; 
                    font-family: 'Segoe MDL2 Assets'; /* Systémový font ikon */
                    font-size: 10px;                  /* Velikost pro tento font */
                    border: none; 
                }}
                QPushButton:hover {{ 
                    color: {COLORS['danger']};        /* Červená při najetí */
                    background-color: rgba(255, 0, 0, 0.1);
                    border-radius: 4px;
                }}
                QPushButton:pressed {{
                    background-color: rgba(255, 0, 0, 0.2);
                }}
            """)
            self.btn.clicked.connect(self.remove_from_queue)
            
        layout.addWidget(self.btn)

    def set_icon(self, pixmap):
        self.current_pixmap = pixmap
        self.icon_lbl.setPixmap(pixmap)
        self.icon_lbl.setText("")

    # --- STAVY TLAČÍTKA (Pro Result Mode) ---
    # --- STAVY TLAČÍTKA (Pro Result Mode) ---
    def set_add_state(self):
        self.btn.setFixedSize(60, 60) # Stejná velikost jako ve frontě
        self.btn.setText("\uE710")    # Systémový znak "Plus"
        self.btn.setToolTip("Přidat do fronty")
        self.btn.setEnabled(True)
        
        self.btn.setStyleSheet(f"""
            QPushButton {{ 
                background-color: transparent; 
                color: #777777; 
                font-family: 'Segoe MDL2 Assets'; 
                font-size: 10px; 
                border: none; 
            }}
            QPushButton:hover {{ 
                color: {COLORS['accent']};  /* Modrá při najetí */
                border-radius: 4px;
            }}
            QPushButton:pressed {{
                background-color: rgba(255, 255, 255, 0.2);
            }}
        """)

    def set_checked_state(self):
        self.btn.setText("✓")
        self.btn.setToolTip("Položka je ve frontě")
        self.btn.setEnabled(False)
        # ZMĚNA STYLU: Plné zelené tlačítko
        self.btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['success']}; 
                color: white; 
                border: none; 
                border-radius: 6px; 
                font-size: 18px;
                font-weight: bold;
            }}
        """)

    def add_to_queue(self):
        self.controller.add_item_to_queue(self.data, cached_icon=self.current_pixmap)
        self.set_checked_state()

    def remove_from_queue(self):
        self.controller.remove_item_from_queue(self.data['id'])

# --- 3. HLAVNÍ UI (InstallerPage) ---
class InstallerPage(QWidget):
    def __init__(self):
        super().__init__()
        self.queue_data = {} 
        self.tooltip_filter = InstantTooltip()

        # Globální tooltip styl
        self.setStyleSheet(f"""
            QToolTip {{
                background-color: {COLORS['item_bg']};
                color: white;
                border: 1px solid {COLORS['accent']};
                border-radius: 4px;
                padding: 6px;
                font-size: 12px;
                font-family: 'Segoe UI';
            }}
        """)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setSpacing(20)

        # === LEVÁ ČÁST (VYHLEDÁVÁNÍ) ===
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        lbl_title = QLabel("Chytrá instalace aplikací")
        lbl_title.setStyleSheet("font-size: 22px; font-weight: bold; color: white;")
        left_layout.addWidget(lbl_title)
        
        lbl_sub = QLabel("Napiš název aplikace nebo funkci (např. 'střih videa').")
        lbl_sub.setStyleSheet("color: #888888; margin-bottom: 10px;")
        left_layout.addWidget(lbl_sub)

        search_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Zadejte dotaz...")
        self.search_input.setStyleSheet(f"""
            QLineEdit {{ 
                background-color: {COLORS['input_bg']}; 
                border: 1px solid {COLORS['border']};
                padding: 10px; font-size: 14px; border-radius: 4px; color: white;
            }}
            QLineEdit:focus {{ border: 1px solid {COLORS['accent']}; }}
        """)
        self.search_input.returnPressed.connect(self.start_search)
        search_row.addWidget(self.search_input)

        self.btn_search = QPushButton("Hledat")
        self.btn_search.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_search.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['accent']}; color: white; border: none;
                padding: 10px 20px; border-radius: 4px; font-weight: bold; font-size: 14px;
            }}
            QPushButton:hover {{ background-color: {COLORS['accent_hover']}; }}
        """)
        self.btn_search.clicked.connect(self.start_search)
        search_row.addWidget(self.btn_search)
        left_layout.addLayout(search_row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0) 
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet(f"""
            QProgressBar {{ min-height: 4px; max-height: 4px; background: transparent; border: none; margin-top: 5px; }} 
            QProgressBar::chunk {{ background-color: {COLORS['accent']}; }}
        """)
        self.progress.hide()
        left_layout.addWidget(self.progress)

        self.results_list = QListWidget()
        # Aplikujeme stejný minimalistický styl i zde
        self.results_list.setStyleSheet(f"""
            QListWidget {{ 
                background-color: {COLORS['bg_sidebar']}; 
                border: none; 
                border-radius: 6px; 
                outline: none; 
            }}
            QListWidget::item {{
                background-color: transparent;
                border: none;
                padding: 0px;
            }}
            
            /* --- MINIMALISTICKÝ SLIDER (SCROLLBAR) --- */
            QScrollBar:vertical {{
                border: none;
                background-color: {COLORS['bg_sidebar']};
                width: 8px;
                margin: 0px 0px 0px 0px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background-color: #444444;
                min-height: 20px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {COLORS['accent']};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
                background: none;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
        """)
        self.results_list.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        left_layout.addWidget(self.results_list)

        main_layout.addWidget(left_panel, stretch=6)

        # === PRAVÁ ČÁST (FRONTA) ===
        right_panel = QWidget()
        right_panel.setStyleSheet(f"background-color: {COLORS['bg_main']};")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        queue_header = QHBoxLayout()
        q_title = QLabel("Instalační fronta")
        q_title.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        queue_header.addWidget(q_title)
        queue_header.addStretch()
        
        self.btn_import = QPushButton("📂")
        self.btn_import.setToolTip("Načíst seznam aplikací ze souboru")
        self._style_icon_btn(self.btn_import)
        self.btn_import.clicked.connect(self.import_queue)
        queue_header.addWidget(self.btn_import)

        self.btn_export = QPushButton("💾")
        self.btn_export.setToolTip("Uložit aktuální seznam aplikací do souboru")
        self._style_icon_btn(self.btn_export)
        self.btn_export.clicked.connect(self.export_queue)
        queue_header.addWidget(self.btn_export)
        
        self.btn_clear = QPushButton("🗑️")
        self.btn_clear.setToolTip("Vymazat celou frontu aplikací")
        self._style_icon_btn(self.btn_clear)
        self.btn_clear.clicked.connect(self.clear_queue)
        queue_header.addWidget(self.btn_clear)
        
        right_layout.addLayout(queue_header)

        self.queue_list = QListWidget()
        # Zde přidáváme sekci pro QScrollBar:vertical
        self.queue_list.setStyleSheet(f"""
            QListWidget {{ 
                background-color: {COLORS['bg_sidebar']}; 
                border: none; 
                border-radius: 6px; 
                outline: none;
            }}
            QListWidget::item {{
                background-color: transparent;
                border: none;
                padding: 0px;
            }}
            QListWidget::item:selected {{
                background-color: transparent;
            }}
            QListWidget::item:hover {{
                background-color: transparent;
            }}

            /* --- MINIMALISTICKÝ SLIDER (SCROLLBAR) --- */
            QScrollBar:vertical {{
                border: none;
                background-color: {COLORS['bg_sidebar']}; /* Pozadí stejné jako seznam */
                width: 8px; /* Tenký slider */
                margin: 0px 0px 0px 0px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background-color: #444444; /* Tmavě šedý jezdec */
                min-height: 20px;
                border-radius: 4px; /* Zakulacený jezdec */
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {COLORS['accent']}; /* Po najetí se zbarví do barvy tématu */
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px; /* Skryje šipky nahoru/dolů */
                background: none;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none; /* Kliknutí do prázdna nic neudělá vizuálně */
            }}
        """)
        self.queue_list.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        right_layout.addWidget(self.queue_list)

        self.btn_save_batch = QPushButton("Uložit instalační soubor")
        self.btn_save_batch.setToolTip("Vytvoří spustitelný .bat soubor, kterým lze nainstalovat aplikace i bez této aplikace.")
        self.btn_save_batch.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save_batch.installEventFilter(self.tooltip_filter)
        self.btn_save_batch.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent; color: {COLORS['accent']}; border: 1px solid {COLORS['accent']};
                padding: 10px; border-radius: 6px; font-weight: bold; font-size: 14px; margin-top: 10px;
            }}
            QPushButton:hover {{ background-color: {COLORS['accent']}; color: white; }}
        """)
        self.btn_save_batch.clicked.connect(self.save_batch_script)
        right_layout.addWidget(self.btn_save_batch)

        self.btn_install = QPushButton("Instalovat vše")
        self.btn_install.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_install.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['success']}; color: white; border: none;
                padding: 15px; border-radius: 6px; font-weight: bold; font-size: 16px; margin-top: 5px;
            }}
            QPushButton:hover {{ background-color: #138913; }}
        """)
        self.btn_install.clicked.connect(self.run_installation)
        right_layout.addWidget(self.btn_install)

        main_layout.addWidget(right_panel, stretch=4)

    def _style_icon_btn(self, btn):
        btn.setFixedSize(40, 40)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.installEventFilter(self.tooltip_filter) 
        btn.setStyleSheet(f"""
            QPushButton {{ 
                background-color: transparent; border: none; color: {COLORS['sub_text']}; 
                font-family: 'Segoe UI Emoji'; font-size: 22px; padding: 0px; margin: 0px;
            }} 
            QPushButton:hover {{ 
                color: {COLORS['accent']}; background-color: {COLORS['item_hover']}; border-radius: 5px;
            }}
            QPushButton:pressed {{ color: white; }}
        """)

    def is_in_queue(self, app_id):
        """Pomocná metoda pro kontrolu, zda je ID ve frontě."""
        return app_id in self.queue_data

    def start_search(self):
        query = self.search_input.text().strip()
        if not query: return
        self.results_list.clear()
        self.btn_search.setEnabled(False)
        self.btn_search.setText("...")
        self.progress.show()
        self.worker = SearchWorker(query)
        self.worker.finished.connect(self.on_search_finished)
        self.worker.error.connect(self.on_search_error)
        self.worker.start()

    def on_search_finished(self, results):
        self.progress.hide()
        self.btn_search.setEnabled(True)
        self.btn_search.setText("Hledat")
        if not results:
            self.show_empty_state("Nic nenalezeno.")
            return
        
        for app in results:
            item = QListWidgetItem(self.results_list)
            item.setSizeHint(QSize(0, 70))
            # Vytvoříme widget a předáme 'self' jako controller
            widget = AppRowWidget(app, 'result', self)
            self.results_list.setItemWidget(item, widget)

    def on_search_error(self, err_msg):
        self.progress.hide()
        self.btn_search.setEnabled(True)
        self.btn_search.setText("Hledat")
        self.show_empty_state(f"Chyba: {err_msg}")

    def show_empty_state(self, message):
        item = QListWidgetItem(self.results_list)
        item.setFlags(Qt.ItemFlag.NoItemFlags)
        widget = QLabel(message)
        widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        widget.setStyleSheet("color: #888; padding: 20px; background: transparent;")
        item.setSizeHint(QSize(0, 100))
        self.results_list.setItemWidget(item, widget)

    def add_item_to_queue(self, data, cached_icon=None):
        app_id = data['id']
        if app_id in self.queue_data: return
        self.queue_data[app_id] = data
        
        item = QListWidgetItem(self.queue_list)
        item.setSizeHint(QSize(0, 50)) 
        item.setData(Qt.ItemDataRole.UserRole, app_id)
        
        # ZDE SE PŘEDÁVÁ IKONA DÁL
        widget = AppRowWidget(data, 'queue', self, cached_icon=cached_icon)
        self.queue_list.setItemWidget(item, widget)

    def remove_item_from_queue(self, app_id):
        # 1. Odstranit z dat
        if app_id in self.queue_data:
            del self.queue_data[app_id]
        
        # 2. Odstranit z vizuálního seznamu fronty
        for i in range(self.queue_list.count()):
            item = self.queue_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == app_id:
                self.queue_list.takeItem(i)
                break
        
        # 3. AKTUALIZACE SEZNAMU VÝSLEDKŮ (Oprava bugu)
        # Projdeme seznam výsledků hledání a pokud tam daná aplikace je, resetujeme tlačítko
        for i in range(self.results_list.count()):
            item = self.results_list.item(i)
            widget = self.results_list.itemWidget(item)
            
            # Musíme ověřit, zda je to AppRowWidget a zda má shodné ID
            if widget and isinstance(widget, AppRowWidget) and widget.data.get('id') == app_id:
                widget.set_add_state() # Reset zpět na "+"

    def clear_queue(self):
        # Uložíme si ID, která mažeme, abychom mohli resetovat tlačítka vlevo
        ids_to_clear = list(self.queue_data.keys())
        
        self.queue_data.clear()
        self.queue_list.clear()
        
        # Reset tlačítek vlevo pro všechna smazaná ID
        for i in range(self.results_list.count()):
            item = self.results_list.item(i)
            widget = self.results_list.itemWidget(item)
            if widget and isinstance(widget, AppRowWidget) and widget.data.get('id') in ids_to_clear:
                widget.set_add_state()

    def export_queue(self):
        if not self.queue_data:
            QMessageBox.warning(self, "Export", "Fronta je prázdná.")
            return
        file_path, _ = QFileDialog.getSaveFileName(self, "Exportovat seznam", "", "JSON Files (*.json)")
        if file_path:
            try:
                data_list = list(self.queue_data.values())
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data_list, f, indent=4)
                QMessageBox.information(self, "Hotovo", "Seznam byl exportován.")
            except Exception as e:
                QMessageBox.critical(self, "Chyba", str(e))

    def import_queue(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Importovat seznam", "", "JSON Files (*.json)")
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data_list = json.load(f)
                count = 0
                for app in data_list:
                    if 'id' in app and 'name' in app:
                        if app['id'] not in self.queue_data:
                            self.add_item_to_queue(app)
                            # Zde bychom ideálně měli také aktualizovat levý panel, pokud tam aplikace je
                            count += 1
                
                # Pro jistotu aktualizujeme všechny tlačítka vlevo
                for i in range(self.results_list.count()):
                    item = self.results_list.item(i)
                    widget = self.results_list.itemWidget(item)
                    if widget and isinstance(widget, AppRowWidget) and self.is_in_queue(widget.data['id']):
                        widget.set_checked_state()

                QMessageBox.information(self, "Hotovo", f"Importováno {count} položek.")
            except Exception as e:
                QMessageBox.critical(self, "Chyba", f"Nepodařilo se načíst soubor:\n{e}")

    def save_batch_script(self):
        if not self.queue_data:
            QMessageBox.warning(self, "Uložit", "Fronta je prázdná.")
            return
        file_path, _ = QFileDialog.getSaveFileName(self, "Uložit instalační skript", "install_all.bat", "Batch Script (*.bat)")
        if file_path:
            try:
                with open(file_path, "w", encoding="cp852") as f:
                    f.write("@echo off\n")
                    f.write("echo Zahajuji instalaci aplikaci (AI Winget Installer)...\n")
                    f.write("echo --------------------------------------------------\n\n")
                    for app in self.queue_data.values():
                        f.write(f"echo Instaluji: {app['name']}...\n")
                        cmd = f'winget install --id "{app["id"]}" -e --silent --accept-package-agreements --accept-source-agreements'
                        f.write(f"{cmd}\n")
                        f.write("echo --------------------------------------------------\n")
                    f.write("\necho HOTOVO! Vse nainstalovano.\n")
                    f.write("pause\n")
                QMessageBox.information(self, "Hotovo", f"Skript uložen:\n{file_path}\n\nStačí na něj poklepat a instalace začne.")
            except Exception as e:
                QMessageBox.critical(self, "Chyba", str(e))

    def run_installation(self):
        if not self.queue_data:
            QMessageBox.warning(self, "Prázdná fronta", "Nejdříve přidejte aplikace do fronty.")
            return
        
        # Převedeme dict na list hodnot (to, co install_manager očekává)
        install_list = list(self.queue_data.values())
        
        # Otevřeme dialog
        dlg = InstallationDialog(install_list, self)
        dlg.exec()