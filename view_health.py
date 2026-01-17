import subprocess
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QScrollArea, QFrame, QMessageBox)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QCursor

from config import COLORS

# --- 1. WIDGET PRO JEDEN NÁSTROJ (ŘÁDEK) ---
# --- 1. WIDGET PRO JEDEN NÁSTROJ (ŘÁDEK) ---
class ToolRowWidget(QWidget):
    def __init__(self, icon, title, desc, command, log_desc, parent_view, is_gui=False):
        super().__init__()
        self.command = command
        self.log_desc = log_desc
        self.parent_view = parent_view
        self.is_gui = is_gui 
        
        # Stylování kontejneru
        self.setStyleSheet(f"""
            QWidget {{ 
                background-color: {COLORS['item_bg']}; 
                border-radius: 8px; 
            }}
            QLabel {{ 
                background-color: transparent; 
                border: none; 
            }}
        """)
        
        # Layout řádku
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(20)
        
        # 1. IKONA
        lbl_icon = QLabel(icon)
        lbl_icon.setFixedSize(40, 40)
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_icon.setStyleSheet("font-size: 24px;") 
        layout.addWidget(lbl_icon)
        
        # 2. TEXTY
        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)
        
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("font-weight: bold; font-size: 15px; color: white;")
        
        lbl_desc = QLabel(desc)
        lbl_desc.setStyleSheet(f"color: {COLORS['sub_text']}; font-size: 12px;")
        lbl_desc.setWordWrap(True)
        
        text_layout.addWidget(lbl_title)
        text_layout.addWidget(lbl_desc)
        
        layout.addLayout(text_layout, stretch=1)
        
        # 3. TLAČÍTKO SPUSTIT (Nový vzhled)
        btn_run = QPushButton("▶  Spustit")
        btn_run.setFixedSize(110, 36) # Širší, nižší (klasický button)
        btn_run.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_run.setToolTip(f"Spustit {title}")
        
        # Moderní "Outline" styl (Obrys -> Výplň při hoveru)
        btn_run.setStyleSheet(f"""
            QPushButton {{ 
                background-color: transparent; 
                color: {COLORS['accent']}; 
                border: 1px solid {COLORS['accent']}; 
                border-radius: 6px; 
                font-size: 13px;
                font-weight: bold;
                text-align: center;
            }}
            QPushButton:hover {{ 
                background-color: {COLORS['accent']}; 
                color: white; 
                border: 1px solid {COLORS['accent']};
            }}
            QPushButton:pressed {{
                background-color: {COLORS['accent_hover']};
                border-color: {COLORS['accent_hover']};
            }}
        """)
        btn_run.clicked.connect(self.run_tool)
        layout.addWidget(btn_run)

    def run_tool(self):
        self.parent_view.execute_tool(self.command, self.log_desc, self.is_gui)
        
# --- 2. HLAVNÍ STRÁNKA (HEALTH CHECK) ---
class HealthCheckPage(QWidget):
    def __init__(self):
        super().__init__()
        
        # Hlavní Layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setSpacing(20)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Header
        header_layout = QVBoxLayout()
        header_layout.setSpacing(5)
        
        lbl_head = QLabel("Kontrola stavu PC")
        lbl_head.setStyleSheet("font-size: 28px; font-weight: bold; color: white;")
        header_layout.addWidget(lbl_head)
        
        lbl_info = QLabel("Nástroje se otevřou v novém okně příkazového řádku.")
        lbl_info.setStyleSheet(f"color: {COLORS['sub_text']}; font-size: 14px;")
        header_layout.addWidget(lbl_info)
        
        main_layout.addLayout(header_layout)
        main_layout.addSpacing(10)

        # Scroll Area s moderním sliderem
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        # === MODERNÍ SCROLLBAR CSS ===
        scroll.setStyleSheet(f"""
            QScrollArea {{ border: none; background: transparent; }} 
            QWidget {{ background: transparent; }}
            
            /* Svislý posuvník (Slider) */
            QScrollBar:vertical {{
                border: none;
                background: {COLORS['bg_main']}; /* Pozadí dráhy */
                width: 10px; /* Tenký slider */
                margin: 0px 0px 0px 0px;
                border-radius: 5px;
            }}
            
            /* Úchyt (Handle) */
            QScrollBar::handle:vertical {{
                background-color: #444; /* Tmavě šedá */
                min-height: 30px;
                border-radius: 5px; /* Zaoblené rohy */
            }}
            
            /* Hover efekt na úchyt */
            QScrollBar::handle:vertical:hover {{
                background-color: {COLORS['accent']}; /* Zmodrá při najetí */
            }}
            
            /* Skrytí šipek nahoře a dole */
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
                background: none;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
        """)
        
        tools_container = QWidget()
        tools_layout = QVBoxLayout(tools_container)
        tools_layout.setSpacing(12)
        tools_layout.setContentsMargins(0, 0, 15, 0) # Padding vpravo kvůli scrollbaru

        # >> SEKCE: OPRAVY SYSTÉMU
        tools_layout.addWidget(self._create_section_label("Opravy Systému"))
        
        self._add_tool(tools_layout, "🔍", "SFC Scan", "Kontrola a automatická oprava poškozených systémových souborů.", 
                       "sfc /scannow", "SFC Scan")
        
        self._add_tool(tools_layout, "💾", "CHKDSK Scan", "Rychlá kontrola chyb na disku C: (režim pouze pro čtení).", 
                       "chkdsk C: /scan", "Check Disk")
        
        self._add_tool(tools_layout, "🩺", "DISM Check", "Diagnostika obrazu Windows (zjistí poškození).", 
                       "dism /online /cleanup-image /CheckHealth", "DISM Check")
        
        self._add_tool(tools_layout, "🛠️", "DISM Restore", "Stáhne a opraví systémové soubory z Windows Update.", 
                       "dism /online /cleanup-image /RestoreHealth", "DISM Restore")

        # >> SEKCE: ÚDRŽBA
        tools_layout.addWidget(self._create_section_label("Správa a Údržba"))

        self._add_tool(tools_layout, "🗑️", "Smazat Temp", "Bezpečně vymaže dočasné soubory.", 
                       'del /q/f/s %TEMP%\\*', "Temp Cleaner")
        
        self._add_tool(tools_layout, "💿", "Vyčištění Disku", "Otevře nástroj Windows Disk Cleanup.", 
                       "cleanmgr.exe", "Disk Cleanup", is_gui=True)
        
        self._add_tool(tools_layout, "🔋", "Report Baterie", "Uloží HTML report o baterii na disk C:.", 
                       "powercfg /batteryreport /output \"C:\\battery_report.html\"", "Battery Report")
        
        self._add_tool(tools_layout, "🧹", "WinSxS Cleanup", "Hloubkové čištění starých aktualizací (úspora místa).", 
                       "dism /online /cleanup-image /StartComponentCleanup", "Component Cleanup")

        tools_layout.addStretch()
        scroll.setWidget(tools_container)
        main_layout.addWidget(scroll)

    # --- POMOCNÉ METODY ---

    def _create_section_label(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {COLORS['accent']}; font-weight: bold; font-size: 16px; margin-top: 15px; margin-bottom: 5px;")
        return lbl

    def _add_tool(self, layout, icon, title, desc, command, log_name, is_gui=False):
        widget = ToolRowWidget(icon, title, desc, command, log_name, self, is_gui)
        layout.addWidget(widget)

    # --- LOGIKA SPUŠTĚNÍ ---

    def execute_tool(self, command, desc, is_gui):
        """
        Spustí nástroj.
        CLI: Otevře CMD okno. Pomocí 'mode con' nastavíme velikost 100x30, 
        což donutí Windows okno lépe pozicovat (často na střed/kaskádu) a vypadá to profesionálněji.
        """
        try:
            if is_gui:
                subprocess.Popen(command, shell=True)
            else:
                # 1. Nastavíme titulek okna
                # 2. Nastavíme velikost okna (cols=100 lines=30) pro lepší viditelnost
                # 3. Spustíme samotný příkaz
                # && = provést další příkaz, jen pokud ten předchozí uspěl
                
                cmd_with_resize = f'mode con: cols=100 lines=30 && color 0A && echo --- SPUSTENO: {desc} --- && {command}'
                
                full_cmd = f'start "AI Winget - {desc}" cmd /k "{cmd_with_resize}"'
                
                subprocess.Popen(full_cmd, shell=True)

        except Exception as e:
            QMessageBox.critical(self, "Chyba spuštění", str(e))