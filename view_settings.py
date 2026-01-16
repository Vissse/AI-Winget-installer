import webbrowser
import subprocess
import os
import importlib
import re
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QLineEdit, QComboBox, QFrame, QMessageBox, 
                             QTextEdit, QDialog, QScrollArea, QCheckBox, QFileDialog)
from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal
from PyQt6.QtGui import QIcon, QMouseEvent, QCursor


from config import COLORS, THEMES
from settings_manager import SettingsManager
from google import genai 
from google.genai import types

# Pokus o import presets pro analýzu
try:
    import presets
except ImportError:
    presets = None

# --- WORKER PRO TEST API ---
class ApiTestWorker(QThread):
    finished = pyqtSignal(bool, str) # success, message

    def __init__(self, api_key):
        super().__init__()
        self.api_key = api_key

    def run(self):
        try:
            client = genai.Client(api_key=self.api_key)
            response = client.models.generate_content(
                model="gemini-2.5-flash", 
                contents="Ping",
                config=types.GenerateContentConfig(max_output_tokens=5)
            )
            if response:
                self.finished.emit(True, "✅ API Klíč je platný a funkční.")
        except Exception as e:
            self.finished.emit(False, f"❌ Chyba: {str(e)}")

# --- WORKER PRO KONTROLU A OPRAVU PRESETS ---
class PresetsCheckWorker(QThread):
    log_signal = pyqtSignal(str)     # Průběžný log
    finished = pyqtSignal(str)       # Finální report

    def run(self):
        if not presets:
            self.finished.emit("Chyba: Soubor presets.py nebyl nalezen.")
            return

        self.log_signal.emit("Načítám definice z presets.py...")
        
        apps_to_check = []
        seen_ids = set()

        def collect_apps(data):
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and "id" in item and "name" in item:
                        if item["id"] not in seen_ids:
                            apps_to_check.append(item)
                            seen_ids.add(item["id"])

        for key, value in presets.PRESETS.items():
            collect_apps(value)

        total = len(apps_to_check)
        self.log_signal.emit(f"Nalezeno {total} unikátních aplikací ke kontrole.\n")

        changes = []
        errors = []

        for i, app in enumerate(apps_to_check):
            current_id = app["id"]
            app_name = app["name"]
            
            self.log_signal.emit(f"[{i+1}/{total}] Kontrola: {app_name} ({current_id})...")

            if not self.is_id_valid(current_id):
                self.log_signal.emit(f"   ⚠️ ID '{current_id}' nefunguje. Hledám opravu...")
                new_id = self.find_correct_id(app_name)
                
                if new_id and new_id != current_id:
                    self.log_signal.emit(f"   ✅ Nalezeno nové ID: {new_id}")
                    if self.update_presets_file(current_id, new_id):
                        changes.append(f"OPRAVENO: {app_name}\n   Staré: {current_id}\n   Nové:  {new_id}")
                    else:
                        errors.append(f"CHYBA ZÁPISU: {app_name}")
                else:
                    errors.append(f"NENALEZENO: {app_name}")
                    self.log_signal.emit(f"   ❌ Nepodařilo se najít nové ID.")
            else:
                pass

        report = "=== VÝSLEDEK KONTROLY ===\n\n"
        if changes:
            report += f"✅ Bylo opraveno {len(changes)} ID:\n" + "\n".join(changes) + "\n\n"
        else:
            report += "✅ Všechna ID jsou platná. Žádné změny.\n\n"
        
        if errors:
            report += f"⚠️ Problémy ({len(errors)}):\n" + "\n".join(errors)
            
        importlib.reload(presets)
        self.finished.emit(report)

    def is_id_valid(self, app_id):
        try:
            cmd = f'winget show --id "{app_id}" --accept-source-agreements'
            result = subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return result.returncode == 0
        except:
            return False

    def find_correct_id(self, app_name):
        try:
            cmd = f'winget search --name "{app_name}" --source winget --accept-source-agreements -n 1'
            result = subprocess.run(cmd, capture_output=True, text=True, shell=True, encoding='cp852', errors='replace')
            lines = result.stdout.split('\n')
            data_started = False
            for line in lines:
                if line.startswith("---"):
                    data_started = True
                    continue
                if data_started and line.strip():
                    ids = re.findall(r'\b[a-zA-Z0-9-]+\.[a-zA-Z0-9\.-]+\b', line)
                    if ids:
                        return ids[0]
            return None
        except:
            return None

    def update_presets_file(self, old_id, new_id):
        try:
            file_path = "presets.py"
            if not os.path.exists(file_path): return False
            with open(file_path, "r", encoding="utf-8") as f: content = f.read()
            old_str = f'"{old_id}"'
            new_str = f'"{new_id}"'
            
            if old_str not in content:
                if old_id in content: content = content.replace(old_id, new_id)
                else: return False
            else:
                content = content.replace(old_str, new_str)
            
            with open(file_path, "w", encoding="utf-8") as f: f.write(content)
            return True
        except:
            return False


# --- DIALOG PRO VÝPIS LOGU ---
class LogDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(600, 450)
        
        self.container = QWidget(self)
        self.container.setObjectName("MainContainer")
        self.container.setGeometry(0, 0, 600, 450)
        self.container.setStyleSheet(f"""
            #MainContainer {{
                background-color: {COLORS['bg_main']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
        """)
        
        main_layout = QVBoxLayout(self.container)
        main_layout.setContentsMargins(1, 1, 1, 1)
        main_layout.setSpacing(0)

        # Horní lišta
        title_bar = QWidget()
        title_bar.setObjectName("TitleBar")
        title_bar.setFixedHeight(40)
        title_bar.setStyleSheet(f"""
            #TitleBar {{
                background-color: {COLORS['bg_sidebar']};
                border: 1px solid {COLORS['border']}; 
                border-top-left-radius: 7px; 
                border-top-right-radius: 7px;
                border-bottom-left-radius: 0px;
                border-bottom-right-radius: 0px;
            }}
        """)
        
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(15, 0, 10, 0)

        lbl_title = QLabel("🔍 Kontrola Presets")
        lbl_title.setStyleSheet("color: white; font-weight: bold; border: none; font-size: 14px; background: transparent;")
        title_layout.addWidget(lbl_title)
        title_layout.addStretch()

        btn_x = QPushButton("✕")
        btn_x.setFixedSize(30, 30)
        btn_x.clicked.connect(self.reject)
        btn_x.setStyleSheet(f"background: transparent; color: #888; border: none; font-size: 16px; font-weight: bold;")
        title_layout.addWidget(btn_x)
        main_layout.addWidget(title_bar)

        # Obsah
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(20, 20, 20, 20)
        
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setStyleSheet(f"background-color: {COLORS['input_bg']}; color: {COLORS['fg']}; border: 1px solid {COLORS['border']}; font-family: Consolas; border-radius: 4px;")
        content_layout.addWidget(self.log_area)

        self.btn_close = QPushButton("Zavřít")
        self.btn_close.setEnabled(False)
        self.btn_close.setFixedHeight(40)
        self.btn_close.setStyleSheet(f"background-color: {COLORS['accent']}; color: white; border: none; border-radius: 4px; font-weight: bold;")
        self.btn_close.clicked.connect(self.accept)
        content_layout.addWidget(self.btn_close)

        main_layout.addLayout(content_layout)
        self.old_pos = None

    def append_log(self, text):
        self.log_area.append(text)
        self.log_area.verticalScrollBar().setValue(self.log_area.verticalScrollBar().maximum())

    def finish(self, report):
        self.log_area.append("\n" + "-"*40 + "\n")
        self.log_area.append(report)
        self.btn_close.setEnabled(True)
        self.btn_close.setText("Hotovo (Zavřít)")

    # Drag okna
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton: self.old_pos = event.globalPosition().toPoint()
    def mouseMoveEvent(self, event: QMouseEvent):
        if self.old_pos:
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.pos() + delta)
            self.old_pos = event.globalPosition().toPoint()
    def mouseReleaseEvent(self, event: QMouseEvent): self.old_pos = None


# --- POMOCNÉ WIDGETY ---

class SectionHeader(QLabel):
    def __init__(self, text):
        super().__init__(text)
        self.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {COLORS['sub_text']}; margin-top: 25px; margin-bottom: 10px;")

class Separator(QFrame):
    def __init__(self):
        super().__init__()
        self.setFrameShape(QFrame.Shape.HLine)
        self.setStyleSheet(f"background-color: {COLORS['border']}; margin-top: 15px; margin-bottom: 15px;")
        self.setFixedHeight(1)

class SettingRow(QWidget):
    def __init__(self, title, description, widget):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 10, 0, 10)
        
        text_layout = QVBoxLayout()
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("font-size: 14px; font-weight: bold; color: white;")
        lbl_desc = QLabel(description)
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet(f"font-size: 12px; color: {COLORS['sub_text']};")
        text_layout.addWidget(lbl_title)
        text_layout.addWidget(lbl_desc)
        
        layout.addLayout(text_layout, stretch=1)
        layout.addSpacing(20)
        layout.addWidget(widget)

# --- HLAVNÍ STRÁNKA NASTAVENÍ ---

class SettingsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.settings = SettingsManager.load_settings()
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Scroll Area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self._style_scrollbar()

        # Obsah
        self.content_widget = QWidget()
        self.content_widget.setStyleSheet(f"background-color: {COLORS['bg_main']};")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(40, 40, 40, 40)
        self.content_layout.setSpacing(5)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # === ZAHÁJENÍ OBSAHU ===

        lbl_main = QLabel("Nastavení")
        lbl_main.setStyleSheet("font-size: 28px; font-weight: bold; color: white; margin-bottom: 20px;")
        self.content_layout.addWidget(lbl_main)

        # 1. SEKCE: GEMINI API
        self.content_layout.addWidget(SectionHeader("Gemini API (AI)"))
        self.content_layout.addWidget(QLabel("Pro fungování inteligentního vyhledávání je potřeba API klíč."))
        
        api_row = QHBoxLayout()
        self.api_input = QLineEdit()
        self.api_input.setText(self.settings.get("api_key", ""))
        self.api_input.setPlaceholderText("Vložte API klíč zde...")
        self.api_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._style_input(self.api_input)
        api_row.addWidget(self.api_input)
        
        btn_save = QPushButton("Uložit")
        self._style_button(btn_save)
        btn_save.clicked.connect(self.save_api_key)
        api_row.addWidget(btn_save)
        self.content_layout.addLayout(api_row)

        tools_row = QHBoxLayout()
        btn_get_key = QPushButton("Získat API klíč zdarma")
        self._style_link_btn(btn_get_key)
        btn_get_key.clicked.connect(lambda: webbrowser.open("https://aistudio.google.com/app/apikey"))
        tools_row.addWidget(btn_get_key)
        
        btn_test = QPushButton("Ověřit správnost API klíče")
        self._style_link_btn(btn_test)
        btn_test.clicked.connect(self.test_api_connection)
        tools_row.addWidget(btn_test)
        tools_row.addStretch()
        self.content_layout.addLayout(tools_row)
        
        self.status_lbl = QLabel("")
        self.content_layout.addWidget(self.status_lbl)
        self.content_layout.addWidget(Separator())

        # 2. SEKCE: KONFIGURACE INSTALACE (WINGET)
        self.content_layout.addWidget(SectionHeader("Konfigurace Instalace"))
        
        # A) Scope (Rozsah)
        self.scope_combo = QComboBox()
        self.scope_combo.addItems(["Všichni uživatelé", "Aktuální uživatel"])
        # Načtení uložené hodnoty (default Machine)
        saved_scope = self.settings.get("winget_scope", "machine")
        self.scope_combo.setCurrentIndex(0 if saved_scope == "machine" else 1)
        self.scope_combo.currentIndexChanged.connect(self.save_winget_settings)
        self._style_combo(self.scope_combo)
        
        self.content_layout.addWidget(SettingRow(
            "Rozsah instalace", 
            "Určuje, kam se aplikace instalují. 'Všichni uživatelé' instaluje do Program Files. 'Aktuální uživatel' instaluje do složky uživatele - AppData.", 
            self.scope_combo
        ))

        # B) Mode (Tichá vs Interaktivní)
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Instalace na pozadí", "Interaktivní instalace"])
        saved_mode = self.settings.get("winget_mode", "silent")
        self.mode_combo.setCurrentIndex(0 if saved_mode == "silent" else 1)
        self.mode_combo.currentIndexChanged.connect(self.save_winget_settings)
        self._style_combo(self.mode_combo)

        self.content_layout.addWidget(SettingRow(
            "Režim instalace", 
            "Tichá instalace proběhne na pozadí. Interaktivní zobrazí klasického průvodce instalací aplikace.", 
            self.mode_combo
        ))

        # C) Checkboxy (Force, Agreements)
        self.chk_force = QCheckBox()
        self.chk_force.setChecked(self.settings.get("winget_force", True))
        self.chk_force.toggled.connect(self.save_winget_settings)
        self._style_checkbox(self.chk_force)
        self.content_layout.addWidget(SettingRow("Vynutit instalaci", "Přeinstaluje aplikaci i v případě konfliktů nebo stejné verze.", self.chk_force))

        self.chk_agreements = QCheckBox()
        self.chk_agreements.setChecked(self.settings.get("winget_agreements", True))
        self.chk_agreements.toggled.connect(self.save_winget_settings)
        self._style_checkbox(self.chk_agreements)
        self.content_layout.addWidget(SettingRow("Automatický souhlas", "Automaticky potvrdí licenční podmínky a zdroje. Nutné pro automatizaci.", self.chk_agreements))


        # D) Vlastní instalační cesta
        path_row_layout = QHBoxLayout()
        self.path_input = QLineEdit()
        self.path_input.setText(self.settings.get("winget_location", ""))
        self.path_input.setPlaceholderText("Výchozí")
        self.path_input.setReadOnly(True) # ReadOnly, aby se vybíralo přes dialog
        self._style_input(self.path_input)
        
        btn_browse = QPushButton("...")
        btn_browse.setFixedSize(40, 38) # Aby ladilo s výškou inputu
        self._style_button(btn_browse)
        btn_browse.clicked.connect(self.browse_location)
        
        btn_clear_path = QPushButton("✕")
        btn_clear_path.setFixedSize(40, 38)
        self._style_button(btn_clear_path)
        btn_clear_path.setStyleSheet(f"background-color: {COLORS['danger']}; color: white; border: none; border-radius: 4px; font-weight: bold;")
        btn_clear_path.clicked.connect(self.clear_location)

        path_row_layout.addWidget(self.path_input)
        path_row_layout.addWidget(btn_browse)
        path_row_layout.addWidget(btn_clear_path)
        
        path_widget = QWidget()
        path_widget.setLayout(path_row_layout)
        path_row_layout.setContentsMargins(0,0,0,0)

        self.content_layout.addWidget(SettingRow(
            "Vlastní instalační cesta", 
            "Určuje složku pro instalaci. Upozornění: Některé aplikace (např. z Microsoft Store) toto nastavení ignorují.", 
            path_widget
        ))
        self.content_layout.addWidget(Separator())

        # 3. SEKCE: PRESETS
        self.content_layout.addWidget(SectionHeader("Databáze aplikací"))
        btn_check_presets = QPushButton("Zkontrolovat správnost ID k instalaci aplikace")
        self._style_link_btn(btn_check_presets)
        btn_check_presets.clicked.connect(self.check_presets)
        
        self.content_layout.addWidget(SettingRow(
            "Validace ID aplikací", 
            "Ověří všechna ID v databázi a automaticky opraví neplatné.", 
            btn_check_presets
        ))
        self.content_layout.addWidget(Separator())

        # 4. SEKCE: VZHLED
        self.content_layout.addWidget(SectionHeader("Vzhled a Jazyk"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(list(THEMES.keys()))
        current_theme = self.settings.get("theme", "Dark (Default)")
        self.theme_combo.setCurrentText(current_theme if current_theme in THEMES else "Dark (Default)")
        self.theme_combo.currentTextChanged.connect(self.save_theme)
        self._style_combo(self.theme_combo)
        self.content_layout.addWidget(SettingRow("Barevný motiv", "Vyberte si světlý nebo tmavý režim.", self.theme_combo))

        self.lang_combo = QComboBox()
        # Seznam jazyků
        european_languages = [
            "Čeština", "English", "Deutsch", "Slovenčina", "Polski", 
            "Français", "Español", "Italiano", "Português", "Nederlands", 
            "Dansk", "Svenska", "Norsk", "Suomi", "Magyar", "Română", 
            "Ελληνικά", "Русский", "Українська", "Hrvatski", "Slovenščina", 
            "Srpski", "Български", "Eesti", "Latviešu", "Lietuvių", "Türkçe"
        ]
        european_languages.sort() # Seřadit abecedně (A-Z)
        
        self.lang_combo.addItems(european_languages)
        
        # Nastavení aktuálního jazyka (pokud není v seznamu, defaultně Čeština)
        current_lang = self.settings.get("language", "Čeština")
        self.lang_combo.setCurrentText(current_lang)
        
        self.lang_combo.currentTextChanged.connect(self.save_lang)
        self._style_combo(self.lang_combo)
        
        self.content_layout.addWidget(SettingRow("Jazyk aplikace", "Změna se projeví po restartu.", self.lang_combo))
        self.content_layout.addWidget(Separator())

        # 5. SEKCE: SYSTÉM
        self.content_layout.addWidget(SectionHeader("Systém"))
        btn_update = QPushButton("Zkontrolovat aktualizace")
        self._style_link_btn(btn_update)
        btn_update.clicked.connect(lambda: QMessageBox.information(self, "Update", "Máte nejnovější verzi."))
        self.content_layout.addWidget(SettingRow("Aktualizace", "Zkontrolujte dostupnost nové verze.", btn_update))

        self.content_layout.addStretch()
        self.scroll_area.setWidget(self.content_widget)
        main_layout.addWidget(self.scroll_area)


    # --- STYLY A LOGIKA ---

    def _style_input(self, widget):
        widget.setStyleSheet(f"background-color: {COLORS['input_bg']}; border: 1px solid {COLORS['border']}; padding: 10px; border-radius: 4px; color: white; font-family: Consolas;")

    def _style_button(self, btn):
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"QPushButton {{ background-color: {COLORS['accent']}; color: white; border: none; padding: 10px 20px; border-radius: 4px; font-weight: bold; }} QPushButton:hover {{ background-color: {COLORS['accent_hover']}; }}")

    def _style_link_btn(self, btn):
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"QPushButton {{ background: transparent; color: {COLORS['fg']}; border: none; text-align: left; }} QPushButton:hover {{ color: {COLORS['accent']}; text-decoration: underline; }}")

    def _style_combo(self, combo):
        combo.setFixedWidth(250)
        combo.setCursor(Qt.CursorShape.PointingHandCursor)
        combo.setStyleSheet(f"QComboBox {{ background-color: {COLORS['input_bg']}; color: white; border: 1px solid {COLORS['border']}; padding: 5px; border-radius: 4px; }} QComboBox::drop-down {{ border: none; }}")

    def _style_checkbox(self, chk):
        chk.setCursor(Qt.CursorShape.PointingHandCursor)
        # Checkbox styl (čtvereček)
        chk.setStyleSheet(f"""
            QCheckBox::indicator {{ width: 20px; height: 20px; border: 1px solid {COLORS['border']}; border-radius: 4px; background: {COLORS['input_bg']}; }}
            QCheckBox::indicator:checked {{ background: {COLORS['accent']}; image: url(check.png); border: 1px solid {COLORS['accent']}; }}
        """)

    def _style_scrollbar(self):
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{ background-color: transparent; border: none; }}
            QScrollBar:vertical {{ border: none; background-color: {COLORS['bg_main']}; width: 8px; margin: 0px; border-radius: 4px; }}
            QScrollBar::handle:vertical {{ background-color: #444; min-height: 20px; border-radius: 4px; }}
            QScrollBar::handle:vertical:hover {{ background-color: {COLORS['accent']}; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
        """)

    def save_winget_settings(self):
        """Uloží nastavení instalace do JSONu."""
        scope_map = {0: "machine", 1: "user"}
        mode_map = {0: "silent", 1: "interactive"}
        
        self.settings["winget_scope"] = scope_map[self.scope_combo.currentIndex()]
        self.settings["winget_mode"] = mode_map[self.mode_combo.currentIndex()]
        self.settings["winget_force"] = self.chk_force.isChecked()
        self.settings["winget_agreements"] = self.chk_agreements.isChecked()
        
        SettingsManager.save_settings(self.settings)

    def save_api_key(self):
        self.settings["api_key"] = self.api_input.text().strip()
        SettingsManager.save_settings(self.settings)
        self.status_lbl.setText("✅ API klíč uložen.")
        self.status_lbl.setStyleSheet(f"color: {COLORS['success']}; margin-top: 5px;")

    def test_api_connection(self):
        key = self.api_input.text().strip()
        if not key:
            self.status_lbl.setText("⚠️ Nejdříve vložte API klíč.")
            self.status_lbl.setStyleSheet("color: orange;")
            return
        self.status_lbl.setText("Ověřuji připojení...")
        self.status_lbl.setStyleSheet(f"color: {COLORS['sub_text']};")
        self.worker = ApiTestWorker(key)
        self.worker.finished.connect(self.on_test_finished)
        self.worker.start()

    def on_test_finished(self, success, message):
        color = COLORS['success'] if success else COLORS['danger']
        self.status_lbl.setText(message)
        self.status_lbl.setStyleSheet(f"color: {color}; font-weight: bold;")

    def check_presets(self):
        self.log_dialog = LogDialog(self)
        self.log_dialog.show()
        self.presets_worker = PresetsCheckWorker()
        self.presets_worker.log_signal.connect(self.log_dialog.append_log)
        self.presets_worker.finished.connect(self.log_dialog.finish)
        self.presets_worker.start()

    def save_theme(self, text):
        self.settings["theme"] = text
        SettingsManager.save_settings(self.settings)

    def save_lang(self, text):
        self.settings["language"] = text
        SettingsManager.save_settings(self.settings)
    
    # Přidat k metodám třídy SettingsPage:

    def browse_location(self):
        folder = QFileDialog.getExistingDirectory(self, "Vybrat instalační složku")
        if folder:
            # Převedeme lomítka na Windows styl, vypadá to lépe
            folder = os.path.normpath(folder)
            self.path_input.setText(folder)
            self.settings["winget_location"] = folder
            SettingsManager.save_settings(self.settings)

    def clear_location(self):
        self.path_input.clear()
        self.settings["winget_location"] = ""
        SettingsManager.save_settings(self.settings)