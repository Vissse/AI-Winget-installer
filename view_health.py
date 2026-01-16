import subprocess
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTextEdit, QScrollArea, QFrame)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QTextCursor

from config import COLORS

# --- 1. WORKER PRO PŘÍKAZOVÝ ŘÁDEK ---
# Běží na pozadí, čte výstup příkazu a posílá ho do GUI
class CommandWorker(QThread):
    text_received = pyqtSignal(str) # Signál pro nový text
    finished = pyqtSignal()         # Signál pro konec

    def __init__(self, command, desc):
        super().__init__()
        self.command = command
        self.desc = desc

    def run(self):
        self.text_received.emit(f"--- ZAHAJUJI: {self.desc} ---\n")
        self.text_received.emit(f"Příkaz: {self.command}\n\n")

        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            # Úprava pro příkaz 'del'
            full_cmd = f"cmd /c {self.command}" if self.command.startswith("del") else self.command

            process = subprocess.Popen(
                full_cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT, 
                shell=True, 
                bufsize=0, 
                startupinfo=startupinfo
            )
            
            buffer = bytearray()
            
            while True:
                byte = process.stdout.read(1)
                
                if not byte and process.poll() is not None:
                    break
                
                if not byte: continue

                # Detekce konce řádku nebo návratu vozíku (\r - pro procenta)
                if byte == b'\r' or byte == b'\n':
                    if buffer:
                        try:
                            # Dekódování Češtiny (Windows Console cp852)
                            text = buffer.decode('cp852', errors='replace').strip()
                        except:
                            text = buffer.decode('utf-8', errors='replace').strip()
                        
                        if text:
                            self.text_received.emit(text + "\n")
                        
                        buffer = bytearray()
                else:
                    buffer.extend(byte)
            
            rc = process.poll()
            if rc == 0:
                self.text_received.emit("\n✅ HOTOVO: Operace úspěšná.\n")
            else:
                self.text_received.emit(f"\n❌ CHYBA (Kód {rc}).\nUjistěte se, že běžíte jako SPRÁVCE.\n")

        except Exception as e:
            self.text_received.emit(f"Kritická chyba: {str(e)}\n")
        
        self.finished.emit()

# --- 2. WIDGET PRO JEDEN NÁSTROJ (ŘÁDEK) ---
class ToolRowWidget(QWidget):
    def __init__(self, icon, title, desc, command, log_desc, parent_view):
        super().__init__()
        self.command = command
        self.log_desc = log_desc
        self.parent_view = parent_view
        
        # Stylování kontejneru
        self.setStyleSheet(f"""
            QWidget {{ background-color: {COLORS['item_bg']}; border-radius: 6px; }}
            QLabel {{ background-color: transparent; border: none; }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Ikona
        lbl_icon = QLabel(icon)
        lbl_icon.setStyleSheet("font-size: 20px;")
        layout.addWidget(lbl_icon)
        
        # Texty
        text_layout = QVBoxLayout()
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("font-weight: bold; font-size: 14px; color: white;")
        
        lbl_desc = QLabel(desc)
        lbl_desc.setStyleSheet(f"color: {COLORS['sub_text']}; font-size: 11px;")
        lbl_desc.setWordWrap(True)
        
        text_layout.addWidget(lbl_title)
        text_layout.addWidget(lbl_desc)
        layout.addLayout(text_layout)
        
        # Tlačítko Spustit
        btn_run = QPushButton("▶")
        btn_run.setFixedSize(30, 30)
        btn_run.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_run.setToolTip("Spustit nástroj")
        btn_run.setStyleSheet(f"""
            QPushButton {{ 
                background-color: {COLORS['input_bg']}; color: {COLORS['accent']}; 
                border: 1px solid {COLORS['border']}; border-radius: 15px; font-size: 12px;
            }}
            QPushButton:hover {{ 
                background-color: {COLORS['accent']}; color: white; border: none;
            }}
        """)
        btn_run.clicked.connect(self.run_tool)
        layout.addWidget(btn_run)

    def run_tool(self):
        self.parent_view.start_command(self.command, self.log_desc)

# --- 3. HLAVNÍ STRÁNKA (HEALTH CHECK) ---
class HealthCheckPage(QWidget):
    def __init__(self):
        super().__init__()
        
        # Hlavní Layout: Rozdělení na Levý (Tools) a Pravý (Console) panel
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # === LEVÝ PANEL (NÁSTROJE) ===
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # Header
        lbl_head = QLabel("Kontrola stavu PC")
        lbl_head.setStyleSheet("font-size: 22px; font-weight: bold; color: white; margin-bottom: 10px;")
        left_layout.addWidget(lbl_head)

        # Scroll Area pro nástroje (kdyby jich bylo hodně)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea {{ border: none; background: transparent; }} QWidget {{ background: transparent; }}")
        
        tools_container = QWidget()
        tools_layout = QVBoxLayout(tools_container)
        tools_layout.setSpacing(10)
        tools_layout.setContentsMargins(0, 0, 0, 0)

        # >> SEKCE: OPRAVY SYSTÉMU
        tools_layout.addWidget(self._create_section_label("Opravy Systému"))
        
        self._add_tool(tools_layout, "🔍", "SFC Scan", "Kontrola integrity systémových souborů.", 
                       "sfc /scannow", "SFC Scan")
        
        self._add_tool(tools_layout, "💾", "CHKDSK Scan", "Rychlá kontrola chyb na disku C:.", 
                       "chkdsk C: /scan", "Check Disk")
        
        self._add_tool(tools_layout, "🩺", "DISM Check Health", "Diagnostika obrazu Windows.", 
                       "dism /online /cleanup-image /CheckHealth", "DISM Check")
        
        self._add_tool(tools_layout, "🛠️", "DISM Restore Health", "Oprava poškozeného obrazu Windows.", 
                       "dism /online /cleanup-image /RestoreHealth", "DISM Restore")

        # >> SEKCE: ÚDRŽBA
        tools_layout.addWidget(self._create_section_label("Správa a Údržba"))

        self._add_tool(tools_layout, "🗑️", "Smazat Temp", "Vymaže dočasné soubory (%TEMP%).", 
                       'del /q/f/s %TEMP%\\*', "Temp Cleaner")
        
        self._add_tool(tools_layout, "💿", "Vyčištění Disku", "Spustí nástroj Windows Disk Cleanup.", 
                       "cleanmgr.exe", "Disk Cleanup")
        
        self._add_tool(tools_layout, "🔋", "Report Baterie", "Vygeneruje HTML report o zdraví baterie.", 
                       "powercfg /batteryreport /output \"C:\\battery_report.html\"", "Battery Report")
        
        self._add_tool(tools_layout, "🧹", "WinSxS Cleanup", "Hloubkové čištění starých aktualizací.", 
                       "dism /online /cleanup-image /StartComponentCleanup", "Component Cleanup")

        tools_layout.addStretch() # Výplň dolů
        scroll.setWidget(tools_container)
        left_layout.addWidget(scroll)

        main_layout.addWidget(left_panel, stretch=4) # 40% šířky

        # === PRAVÝ PANEL (KONZOLE) ===
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        lbl_console = QLabel("Výstup operace:")
        lbl_console.setStyleSheet(f"color: {COLORS['sub_text']}; font-weight: bold;")
        right_layout.addWidget(lbl_console)
        
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setStyleSheet("""
            QTextEdit {
                background-color: #0d0d0d;
                color: #cccccc;
                font-family: 'Consolas', monospace;
                font-size: 13px;
                border: 1px solid #333;
                border-radius: 4px;
                padding: 10px;
            }
        """)
        right_layout.addWidget(self.console)
        
        main_layout.addWidget(right_panel, stretch=6) # 60% šířky

    # --- POMOCNÉ METODY ---

    def _create_section_label(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {COLORS['accent']}; font-weight: bold; margin-top: 10px; margin-bottom: 5px;")
        return lbl

    def _add_tool(self, layout, icon, title, desc, cmd, log_name):
        widget = ToolRowWidget(icon, title, desc, cmd, log_name, self)
        layout.addWidget(widget)

    # --- LOGIKA SPUŠTĚNÍ ---

    def start_command(self, cmd, log_desc):
        self.console.clear()
        
        # Vytvoření a spuštění vlákna
        self.worker = CommandWorker(cmd, log_desc)
        self.worker.text_received.connect(self.append_log)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def append_log(self, text):
        self.console.moveCursor(QTextCursor.MoveOperation.End)
        self.console.insertPlainText(text)
        self.console.moveCursor(QTextCursor.MoveOperation.End)

    def on_finished(self):
        # Zde můžeme např. odblokovat tlačítka, pokud bychom je blokovali
        pass