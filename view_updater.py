import subprocess
import re
import os
import sys
import winreg
import requests
from urllib.parse import urlparse
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QListWidget, QListWidgetItem, 
                             QProgressBar, QFrame, QLineEdit, QFileIconProvider,
                             QTextEdit, QSizePolicy)
from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal, QFileInfo, QTimer, QPropertyAnimation, QEasingCurve, QAbstractAnimation
from PyQt6.QtGui import QIcon, QTextCursor, QColor, QPixmap, QImage, QPainter
from config import COLORS, resource_path

# Fallback pro HoverButton
try:
    from view_installer import HoverButton
except ImportError:
    class HoverButton(QPushButton):
        def __init__(self, t, i, s, p=None):
            super().__init__(t, p)
            self.setIcon(QIcon(resource_path(i)))

# --- WORKER PRO STAHOVÁNÍ IKON ---
class IconDownloadWorker(QThread):
    loaded = pyqtSignal(QPixmap)

    def __init__(self, app_id):
        super().__init__()
        self.app_id = app_id

    def run(self):
        if not self.app_id: return
        clean_id = self.app_id
        lower_id = self.app_id.lower()
        dashed_id = lower_id.replace(".", "-")
        urls = [
            f"https://cdn.jsdelivr.net/gh/walkxcode/dashboard-icons/png/{dashed_id}.png",
            f"https://cdn.jsdelivr.net/gh/walkxcode/dashboard-icons/png/{lower_id}.png",
            f"https://raw.githubusercontent.com/marticliment/UnigetUI/main/src/UnigetUI.PackageEngine/Assets/Packages/{clean_id}.png",
            f"https://raw.githubusercontent.com/marticliment/UnigetUI/main/src/UnigetUI.PackageEngine/Assets/Packages/{lower_id}.png"
        ]
        session = requests.Session()
        session.headers.update({'User-Agent': 'Mozilla/5.0'})
        for url in urls:
            try:
                response = session.get(url, timeout=1.5, stream=True)
                if response.status_code == 200:
                    data = response.content
                    if len(data) > 50:
                        image = QImage(); image.loadFromData(data)
                        if not image.isNull():
                            pixmap = QPixmap.fromImage(image)
                            self.loaded.emit(pixmap); return
            except: pass

# --- VYLEPŠENÉ HLEDÁNÍ IKON V SYSTÉMU ---
def find_app_icon_path(app_name, app_id=None):
    clean_name = app_name.split(' (')[0].strip()
    search_names = [clean_name.lower()]
    if app_id and "." in app_id:
        publisher = app_id.split('.')[0].lower()
        if len(publisher) > 2: search_names.append(publisher)

    registry_paths = [
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
        r"Software\Microsoft\Windows\CurrentVersion\Uninstall"
    ]
    roots = [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]
    found_install_loc = None

    for i, reg_path in enumerate(registry_paths):
        root = roots[i]
        try:
            with winreg.OpenKey(root, reg_path) as key:
                for j in range(winreg.QueryInfoKey(key)[0]):
                    try:
                        subkey_name = winreg.EnumKey(key, j)
                        with winreg.OpenKey(key, subkey_name) as subkey:
                            try:
                                display_name = winreg.QueryValueEx(subkey, "DisplayName")[0].lower()
                                if any(s in display_name for s in search_names):
                                    try:
                                        display_icon = winreg.QueryValueEx(subkey, "DisplayIcon")[0]
                                        display_icon = display_icon.split(',')[0].strip('"')
                                        if os.path.exists(display_icon) and (display_icon.endswith('.exe') or display_icon.endswith('.ico')):
                                            return display_icon
                                    except: pass
                                    try:
                                        loc = winreg.QueryValueEx(subkey, "InstallLocation")[0].strip('"')
                                        if loc and os.path.exists(loc): found_install_loc = loc
                                    except: pass
                            except: continue
                    except: continue
        except: continue

    if found_install_loc:
        exe = find_main_exe_in_folder(found_install_loc)
        if exe: return exe

    try:
        app_paths_key = r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, app_paths_key) as key:
            for j in range(winreg.QueryInfoKey(key)[0]):
                exe_name = winreg.EnumKey(key, j)
                if clean_name.replace(" ", "").lower() in exe_name.lower():
                    with winreg.OpenKey(key, exe_name) as subkey:
                        try:
                            path = winreg.QueryValue(subkey, None).strip('"')
                            if os.path.exists(path): return path
                        except: pass
    except: pass
    return None

def find_main_exe_in_folder(folder):
    best_exe = None; max_size = 0
    base_depth = folder.rstrip(os.sep).count(os.sep)
    try:
        for root, dirs, files in os.walk(folder):
            current_depth = root.rstrip(os.sep).count(os.sep)
            if current_depth - base_depth > 1: continue 
            for file in files:
                if file.lower().endswith(".exe"):
                    if any(x in file.lower() for x in ["unins", "helper", "crash", "update", "report", "setup"]): continue
                    full_path = os.path.join(root, file)
                    try:
                        size = os.path.getsize(full_path)
                        if "java.exe" in file.lower() or "javaw.exe" in file.lower(): return full_path
                        if size > max_size: max_size = size; best_exe = full_path
                    except: pass
    except: pass
    return best_exe

# --- 1. SCAN WORKER (OPRAVENÝ PARSING PRO <) ---
class ScanWorker(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    
    def run(self):
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            cmd = "winget upgrade --include-unknown --accept-source-agreements"
            
            res = subprocess.run(cmd, capture_output=True, text=True, startupinfo=startupinfo, encoding='utf-8', errors='replace')
            
            updates = []
            parsing = False
            lines = res.stdout.split('\n')
            
            for line in lines:
                clean_line = line.strip()
                if not clean_line: continue
                
                # Detekce hlavičky
                if "Name" in line and "Id" in line and "Version" in line: 
                    parsing = True
                    continue
                if not parsing or "----" in line: 
                    continue
                
                # Filtrace informačních řádků
                if "have an upgrade available" in clean_line or "upgrades available" in clean_line:
                    continue

                # --- PARSOVÁNÍ (ODZADU) ---
                parts = clean_line.split()
                
                # Očekáváme minimálně: Název, ID, StaráVerze, NováVerze, Source (5 dílů, ale název může být rozdělený)
                # Winget výstup:
                # [Název......] [ID] [Stará] [Nová] [Source]
                
                if len(parts) >= 4:
                    source = parts[-1]
                    new_ver = parts[-2]
                    
                    # Logika pro detekci zobáčku <
                    # Normální stav: parts[-3] je verze, parts[-4] je ID
                    # Ubisoft stav: parts[-3] je verze, parts[-4] je <, parts[-5] je ID
                    
                    if parts[-4] == '<':
                        # Případ Ubisoft: verze je rozdělená na "<" a "číslo"
                        curr_ver = f"{parts[-4]} {parts[-3]}" # Spojíme zpět do "< 169.x"
                        app_id = parts[-5]
                        name_parts = parts[:-5]
                    else:
                        # Normální stav
                        curr_ver = parts[-3]
                        app_id = parts[-4]
                        name_parts = parts[:-4]

                    name = " ".join(name_parts)
                    
                    # Fix, pokud by winget chyběl nebo byl posunutý (fallback)
                    if new_ver.lower() == "winget":
                         # Toto se stane jen kdyby winget výstup úplně zblbnul
                         pass

                    updates.append({'name': name, 'id': app_id, 'current': curr_ver, 'new': new_ver})

            self.finished.emit(updates)
        except Exception as e: 
            self.error.emit(str(e))

# --- 2. UPDATE WORKER ---
class UpdateWorker(QThread):
    finished = pyqtSignal()
    log_signal = pyqtSignal(str)

    def __init__(self, app_id=None, update_all=False):
        super().__init__()
        self.app_id = app_id
        self.update_all = update_all
        self.process = None 

    def run(self):
        cmd = ["winget", "upgrade"]
        if self.update_all:
            cmd.extend(["--all", "--include-unknown"])
        else:
            cmd.extend(["--id", self.app_id, "--exact"])
        
        cmd.extend(["--silent", "--disable-interactivity", "--accept-package-agreements", "--accept-source-agreements", "--verbose"])

        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE

        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace',
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                bufsize=1
            )

            for line in self.process.stdout:
                clean_line = line.strip()
                if clean_line:
                    self.log_signal.emit(clean_line)

            self.process.wait()
        except Exception as e:
            self.log_signal.emit(f"CHYBA PROCESU: {str(e)}")
        
        self.finished.emit()

    def kill_process(self):
        if self.process:
            try: self.process.kill() 
            except: pass

# --- 3. UI KOMPONENTY ---

class UpdateRowWidget(QWidget):
    def __init__(self, data, parent_page):
        super().__init__()
        self.data = data
        self.parent_page = parent_page
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(15)

        self.icon_lbl = QLabel()
        self.icon_lbl.setFixedSize(24, 24)
        
        found_local = self.set_local_icon(data['name'], data['id'])
        if not found_local:
            if self.set_system_fallback_icon(data['name']): pass 
            else:
                self.icon_lbl.setText("📦")
                self.icon_lbl.setStyleSheet("font-size: 16px; color: #777; background: transparent;")
                self.dl_worker = IconDownloadWorker(data['id'])
                self.dl_worker.loaded.connect(self.set_downloaded_icon)
                self.dl_worker.start()
        
        layout.addWidget(self.icon_lbl)

        name_lbl = QLabel(data['name'])
        name_lbl.setStyleSheet("font-weight: bold; color: white; background: transparent;")
        layout.addWidget(name_lbl, stretch=1)

        curr_lbl = QLabel(data['current'])
        curr_lbl.setFixedWidth(140)
        curr_lbl.setStyleSheet(f"color: {COLORS['sub_text']}; background: transparent;")
        layout.addWidget(curr_lbl)

        new_lbl = QLabel(data['new'])
        new_lbl.setFixedWidth(140)
        new_lbl.setStyleSheet(f"color: {COLORS['accent']}; font-weight: bold; background: transparent;")
        layout.addWidget(new_lbl)

        self.btn_up = QPushButton("Aktualizovat")
        self.btn_up.setFixedWidth(100)
        self.btn_up.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_up.setStyleSheet(f"""
            QPushButton {{ 
                background: transparent; 
                color: {COLORS['accent']}; 
                font-weight: bold; 
                border: 1px solid {COLORS['accent']}; 
                border-radius: 4px; 
                padding: 4px; 
            }} 
            QPushButton:hover {{ 
                background: {COLORS['accent']}; 
                color: white; 
            }}
        """)
        self.btn_up.clicked.connect(lambda: self.parent_page.run_update(data['id'], data['name']))
        layout.addWidget(self.btn_up)

    def set_local_icon(self, name, app_id):
        icon_path = find_app_icon_path(name, app_id)
        if not icon_path:
            names_to_try = [name]
            if app_id and "." in app_id: names_to_try.append(app_id.split('.')[0])
            for n in names_to_try:
                common_paths = [
                    os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), n),
                    os.path.join(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"), n),
                    os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", n)
                ]
                for path in common_paths:
                    if os.path.exists(path):
                        found_exe = find_main_exe_in_folder(path)
                        if found_exe: icon_path = found_exe; break
                if icon_path: break
                        
        if icon_path and os.path.exists(icon_path):
            pix = QFileIconProvider().icon(QFileInfo(icon_path)).pixmap(24, 24)
            if not pix.isNull():
                self.icon_lbl.setPixmap(pix)
                self.icon_lbl.setStyleSheet("background: transparent;")
                return True
        return False

    def set_system_fallback_icon(self, name):
        n = name.lower()
        icon_name = None
        use_original = False
        
        is_teams = "teams" in n
        
        if any(x in n for x in ["java", "jdk", "jre", "temurin", "oracle"]): 
            icon_name = "java.png"
            use_original = True
        elif any(x in n for x in ["microsoft", "windows", "redist", "c++", ".net"]) and not is_teams:
            icon_name = "windows.png"
            use_original = True
        elif any(x in n for x in ["driver", "realtek", "nvidia", "amd", "intel"]): 
            icon_name = "circuitry-thin.png"
        elif "sdk" in n: 
            icon_name = "code-thin.png"
        
        if icon_name:
            path = resource_path(f"images/{icon_name}")
            if os.path.exists(path):
                pix = QPixmap(path).scaled(22, 22, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                if not use_original:
                    p = QPainter(pix); p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
                    p.fillRect(pix.rect(), QColor(COLORS['sub_text'])); p.end()
                self.icon_lbl.setPixmap(pix)
                return True
        return False

    def set_downloaded_icon(self, pixmap):
        scaled = pixmap.scaled(24, 24, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.icon_lbl.setPixmap(scaled); self.icon_lbl.setText("")

class UpdaterPage(QWidget):
    scan_finished_signal = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.all_updates = [] 
        self.active_workers = []
        self.current_worker = None 

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0); main_layout.setSpacing(0)

        # A. HORNÍ LIŠTA
        top_bar = QWidget()
        top_bar.setStyleSheet(f"background-color: {COLORS['bg_main']}; border-bottom: 1px solid {COLORS['border']};")
        top_l = QHBoxLayout(top_bar); top_l.setContentsMargins(20, 15, 20, 15)
        lbl_t = QLabel("Aktualizace"); lbl_t.setStyleSheet("font-size: 14pt; font-weight: bold; color: white; border: none;")
        top_l.addWidget(lbl_t); top_l.addSpacing(20)

        self.search_container = QFrame()
        self.search_container.setFixedWidth(500); self.search_container.setFixedHeight(38)
        self.search_container.setStyleSheet(f"QFrame {{ background-color: {COLORS['input_bg']}; border: 1px solid {COLORS['border']}; border-radius: 6px; }} QFrame:focus-within {{ border: 1px solid {COLORS['accent']}; }}")
        sl = QHBoxLayout(self.search_container); sl.setContentsMargins(10, 0, 5, 0); sl.setSpacing(0)
        self.search_in = QLineEdit(); self.search_in.setPlaceholderText("Hledat v aktualizacích...")
        self.search_in.setStyleSheet("border: none; color: white; background: transparent; font-size: 10pt;")
        self.search_in.textChanged.connect(self.filter_updates)
        sl.addWidget(self.search_in)
        try:
            btn_s = HoverButton("", "images/magnifying-glass-thin.png", "fg")
            btn_s.setFixedSize(32, 32); btn_s.setIconSize(QSize(18, 18))
        except: btn_s = QLabel("🔍"); btn_s.setStyleSheet("border: none; color: #777;")
        sl.addWidget(btn_s)
        top_l.addWidget(self.search_container); top_l.addStretch()
        main_layout.addWidget(top_bar)

        # B. PROGRESS BAR
        self.progress = QProgressBar(); self.progress.setFixedHeight(2); self.progress.setTextVisible(False)
        self.progress.setStyleSheet(f"QProgressBar {{ background: transparent; border: none; }} QProgressBar::chunk {{ background-color: {COLORS['accent']}; }}")
        self.progress.hide(); main_layout.addWidget(self.progress)

        # C. ACTION BAR
        act_bar = QWidget(); act_bar.setStyleSheet(f"background: {COLORS['bg_main']};")
        al = QHBoxLayout(act_bar); al.setContentsMargins(20, 10, 20, 10); al.setSpacing(10)
        self.btn_scan = QPushButton("  Skenovat")
        self.btn_scan.setIcon(QIcon(resource_path("images/arrows-clockwise-thin.png")))
        self.btn_scan.setFixedHeight(34); self.btn_scan.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_scan.clicked.connect(self.scan_updates)
        self.btn_scan.setStyleSheet(f"QPushButton {{ background: {COLORS['item_bg']}; color: white; border: 1px solid {COLORS['border']}; border-radius: 6px; padding: 0 15px; font-weight: bold; }} QPushButton:hover {{ border-color: {COLORS['accent']}; }}")
        al.addWidget(self.btn_scan)
        self.btn_up_all = QPushButton("  Aktualizovat vše")
        self.btn_up_all.setIcon(QIcon(resource_path("images/download-simple-thin.png")))
        self.btn_up_all.setFixedHeight(34); self.btn_up_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_up_all.setEnabled(False); self.btn_up_all.clicked.connect(self.run_update_all)
        self.btn_up_all.setStyleSheet(f"QPushButton {{ background: {COLORS['accent']}; color: white; border: none; border-radius: 6px; padding: 0 15px; font-weight: bold; }} QPushButton:disabled {{ background: #333; color: #555; }}")
        al.addWidget(self.btn_up_all)
        al.addStretch(); self.status_lbl = QLabel("Připraveno"); self.status_lbl.setStyleSheet(f"color: {COLORS['sub_text']}; font-size: 10pt;")
        al.addWidget(self.status_lbl); main_layout.addWidget(act_bar)

        # D. HLAVIČKA
        head = QWidget(); head.setStyleSheet(f"background: {COLORS['bg_sidebar']}; border-bottom: 1px solid {COLORS['border']};")
        hl = QHBoxLayout(head); hl.setContentsMargins(35, 8, 35, 8); hl.setSpacing(15)
        for t, w, s in [("", 24, 0), ("NÁZEV APLIKACE", 0, 1), ("STÁVAJÍCÍ", 140, 0), ("NOVÁ", 140, 0), ("AKCE", 100, 0)]:
            lbl = QLabel(t); lbl.setStyleSheet(f"font-weight: bold; color: white; font-size: 9pt; border: none;")
            if w > 0: lbl.setFixedWidth(w)
            hl.addWidget(lbl, stretch=s)
        main_layout.addWidget(head)

        # E. SEZNAM
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(f"QListWidget {{ background: {COLORS['bg_main']}; border: none; outline: none; padding: 0 30px; }} QListWidget::item {{ border-bottom: 1px solid {COLORS['border']}; padding: 0px; }} QListWidget::item:hover {{ background: {COLORS['item_hover']}; }} QScrollBar:vertical {{ border: none; background: {COLORS['bg_main']}; width: 8px; margin: 0px; }} QScrollBar::handle:vertical {{ background: #444; min-height: 20px; border-radius: 4px; }} QScrollBar::handle:vertical:hover {{ background: {COLORS['accent']}; }} QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; background: none; }} QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}")
        self.list_widget.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        main_layout.addWidget(self.list_widget)

        # F. KONZOLE
        self.console_container = QFrame(); self.console_container.setMaximumHeight(0)
        self.console_container.setStyleSheet(f"QFrame {{ background-color: {COLORS['bg_sidebar']}; border-top-left-radius: 12px; border-top-right-radius: 12px; border-top: 1px solid #333; }}")
        ccl = QVBoxLayout(self.console_container); ccl.setContentsMargins(15, 8, 15, 8); ccl.setSpacing(5)
        hl = QHBoxLayout(); self.con_title = QLabel("PRŮBĚH INSTALACE")
        self.con_title.setStyleSheet(f"color: white; font-weight: bold; font-size: 11px; letter-spacing: 0.5px; background: transparent;")
        self.btn_cancel = QPushButton("Zrušit"); self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.clicked.connect(self.cancel_current_process)
        self.btn_cancel.setStyleSheet("QPushButton { background: #333; color: #ff5555; border: 1px solid #ff5555; border-radius: 4px; padding: 2px 10px; font-size: 10px; font-weight: bold; } QPushButton:hover { background: #ff5555; color: white; }")
        btn_close = QPushButton("✕"); btn_close.setFixedSize(20, 20); btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet("QPushButton { background: transparent; color: #777; border: none; font-weight: bold; font-size: 12px; } QPushButton:hover { color: white; }")
        btn_close.clicked.connect(self.hide_console)
        hl.addWidget(self.con_title); hl.addStretch(); hl.addWidget(self.btn_cancel); hl.addSpacing(10); hl.addWidget(btn_close)
        ccl.addLayout(hl)
        self.console_out = QTextEdit(); self.console_out.setReadOnly(True)
        self.console_out.setStyleSheet(f"QTextEdit {{ background: transparent; color: #ccc; border: none; font-family: 'Consolas', 'Courier New', monospace; font-size: 11px; }} QScrollBar:vertical {{ border: none; background: transparent; width: 6px; margin: 0; }} QScrollBar::handle:vertical {{ background: #555; min-height: 20px; border-radius: 4px; }} QScrollBar::handle:vertical:hover {{ background: {COLORS['accent']}; }} QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; background: none; }} QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}")
        ccl.addWidget(self.console_out)
        self.con_progress = QProgressBar(); self.con_progress.setFixedHeight(3); self.con_progress.setTextVisible(False)
        self.con_progress.setStyleSheet(f"QProgressBar {{ border: none; background: #222; border-radius: 1px; }} QProgressBar::chunk {{ background-color: {COLORS['accent']}; border-radius: 1px; }}")
        self.con_progress.setRange(0, 0); ccl.addWidget(self.con_progress)
        main_layout.addWidget(self.console_container)
        self.anim = QPropertyAnimation(self.console_container, b"maximumHeight"); self.anim.setDuration(400); self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def scan_updates(self):
        self.list_widget.clear(); self.all_updates = []; self.btn_scan.setEnabled(False); self.btn_up_all.setEnabled(False)
        self.status_lbl.setText("Hledám aktualizace..."); self.progress.setRange(0, 0); self.progress.show()
        self.worker = ScanWorker(); self.worker.finished.connect(self.on_scan_done); self.worker.error.connect(lambda e: self.on_scan_done([])); self.worker.start()

    def on_scan_done(self, updates):
        updates.sort(key=lambda x: x['name'].lower())
        self.progress.hide(); self.btn_scan.setEnabled(True); self.all_updates = updates
        self.render_list(updates); self.scan_finished_signal.emit(updates)
        if updates: self.status_lbl.setText(f"Nalezeno {len(updates)} aktualizací"); self.btn_up_all.setEnabled(True); self.btn_up_all.setText(f"  Aktualizovat vše ({len(updates)})")
        else: self.status_lbl.setText("Vše aktuální")

    def render_list(self, updates):
        self.list_widget.clear()
        for u in updates:
            item = QListWidgetItem(self.list_widget); item.setSizeHint(QSize(0, 60))
            self.list_widget.setItemWidget(item, UpdateRowWidget(u, self))
        if not updates:
            item = QListWidgetItem(self.list_widget); item.setSizeHint(QSize(0, 100))
            l = QLabel("Všechny aplikace jsou aktuální ✨"); l.setAlignment(Qt.AlignmentFlag.AlignCenter); l.setStyleSheet("color: #666; font-size: 14px;"); self.list_widget.setItemWidget(item, l)

    def filter_updates(self, txt):
        f = [u for u in self.all_updates if txt.lower() in u['name'].lower()]
        self.render_list(f)

    def append_log(self, text):
        color = "#cccccc"
        if "Chyba" in text or "Fail" in text or "error" in text.lower(): color = "#ff5555"
        elif "Success" in text or "Successfully" in text: color = "#55ff55"
        elif "Downloading" in text: color = "#55ffff"
        elif "Installing" in text: color = "#ffff55"
        elif "Zrušeno" in text: color = "#ff5555"
        self.console_out.append(f'<span style="color:{color}">{text}</span>')
        self.console_out.verticalScrollBar().setValue(self.console_out.verticalScrollBar().maximum())

    def cleanup_worker(self, worker):
        if worker in self.active_workers: self.active_workers.remove(worker)
        if self.current_worker == worker: self.current_worker = None

    def show_console(self, title):
        self.con_title.setText(title.upper()); self.console_out.clear(); self.con_progress.show(); self.btn_cancel.show()
        self.anim.stop(); self.anim.setStartValue(self.console_container.height()); self.anim.setEndValue(110); self.anim.start()

    def hide_console(self):
        self.anim.stop(); self.anim.setStartValue(self.console_container.height()); self.anim.setEndValue(0); self.anim.start()

    def cancel_current_process(self):
        if self.current_worker:
            self.current_worker.kill_process(); self.append_log("--- Operace Zrušena uživatelem ---")
            self.status_lbl.setText("Zrušeno"); self.con_progress.hide(); self.btn_cancel.hide()
            QTimer.singleShot(1500, self.hide_console)

    def on_update_finished(self, worker, name):
        if worker == self.current_worker:
            self.append_log(f"--- Operace dokončena ---"); self.status_lbl.setText("Hotovo")
            self.con_progress.hide(); self.btn_cancel.hide(); self.scan_updates()
            QTimer.singleShot(3000, self.hide_console)
        self.cleanup_worker(worker)

    def run_update(self, aid, name):
        self.show_console(f"AKTUALIZACE: {name}"); self.append_log(f"Spouštím winget pro {name}...")
        self.status_lbl.setText(f"Aktualizuji {name}...")
        w = UpdateWorker(app_id=aid); self.active_workers.append(w); self.current_worker = w
        w.log_signal.connect(self.append_log); w.finished.connect(lambda: self.on_update_finished(w, name)); w.start()

    def run_update_all(self):
        self.show_console("HROMADNÁ AKTUALIZACE"); self.append_log("Spouštím aktualizaci všech balíčků...")
        self.status_lbl.setText("Probíhá hromadná aktualizace..."); self.list_widget.setEnabled(False)
        w = UpdateWorker(update_all=True); self.active_workers.append(w); self.current_worker = w
        w.log_signal.connect(self.append_log); w.finished.connect(lambda: self.list_widget.setEnabled(True)); w.finished.connect(lambda: self.on_update_finished(w, "Vše")); w.start()