import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from config import COLORS

class FunctionRow(QWidget):
    """Minimalistický řádek funkce s obrázkovou ikonou"""
    def __init__(self, icon_name, title, desc, color_hex):
        super().__init__()
        self.setStyleSheet("background: transparent;")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 10, 0, 10)
        layout.setSpacing(20)
        
        # Ikona
        icon_container = QLabel()
        icon_container.setFixedSize(48, 48)
        icon_container.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_container.setStyleSheet(f"""
            background-color: {COLORS['item_bg']};
            border-radius: 8px;
            border: 1px solid {COLORS['border']};
        """)
        
        # Načtení PNG ikony
        icon_path = os.path.join("images", icon_name)
        if os.path.exists(icon_path):
            pix = QPixmap(icon_path)
            # Přebarvení ikony není triviální bez maskování, 
            # takže použijeme bílou ikonu na tmavém pozadí.
            # Zmenšíme ji trochu, aby měla padding
            pix = pix.scaled(28, 28, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            icon_container.setPixmap(pix)
        else:
            icon_container.setText("?")
            
        layout.addWidget(icon_container)
        
        # Texty
        text_layout = QVBoxLayout()
        text_layout.setSpacing(3)
        
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("font-size: 15px; font-weight: bold; color: white;")
        
        lbl_desc = QLabel(desc)
        lbl_desc.setStyleSheet(f"font-size: 13px; color: {COLORS['sub_text']};")
        lbl_desc.setWordWrap(True)
        
        text_layout.addWidget(lbl_title)
        text_layout.addWidget(lbl_desc)
        layout.addLayout(text_layout)

class HomePage(QWidget):
    def __init__(self):
        super().__init__()
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setSpacing(20)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # 1. HEADER
        try: user = os.getlogin()
        except: user = "Uživatel"
        
        lbl_welcome = QLabel(f"Vítejte, {user}")
        lbl_welcome.setStyleSheet("font-size: 34px; font-weight: bold; color: white;")
        main_layout.addWidget(lbl_welcome)
        
        lbl_intro = QLabel("Toto je centrální rozcestník pro správu vašeho počítače.\nNíže naleznete vysvětlení dostupných modulů.")
        lbl_intro.setStyleSheet(f"font-size: 14px; color: {COLORS['sub_text']}; margin-bottom: 20px;")
        main_layout.addWidget(lbl_intro)

        # 2. SEZNAM FUNKCÍ (Vysvětlivky)
        lbl_funcs_title = QLabel("PŘEHLED MODULŮ")
        lbl_funcs_title.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {COLORS['accent']}; margin-bottom: 10px;")
        main_layout.addWidget(lbl_funcs_title)

        funcs_layout = QVBoxLayout()
        funcs_layout.setSpacing(10)

        funcs_layout.addWidget(FunctionRow(
            "package-thin.png", "Chytrá instalace", 
            "Modul pro rychlé vyhledávání a instalaci aplikací. Využívá repozitář Winget a AI asistenci pro opravu názvů.",
            COLORS['accent']
        ))
        
        funcs_layout.addWidget(FunctionRow(
            "arrows-clockwise-thin.png", "Aktualizace aplikací", 
            "Automaticky skenuje nainstalovaný software a nabídne hromadnou aktualizaci zastaralých verzí.",
            COLORS['success']
        ))
        
        funcs_layout.addWidget(FunctionRow(
            "trash-simple-thin.png", "Odinstalace aplikací", 
            "Přehledný seznam všech nainstalovaných programů s možností jejich čistého odstranění.",
            "#d63031"
        ))
        
        funcs_layout.addWidget(FunctionRow(
            "heartbeat-thin.png", "Kontrola stavu PC", 
            "Sada diagnostických nástrojů: kontrola systémových souborů, stav baterie, čištění disku a optimalizace.",
            "#0984e3"
        ))
        
        funcs_layout.addWidget(FunctionRow(
            "desktop-thin.png", "Specifikace PC", 
            "Detailní výpis hardwarových komponent vašeho počítače (Procesor, Grafika, RAM, Základní deska).",
            "#6c5ce7"
        ))

        main_layout.addLayout(funcs_layout)
        main_layout.addStretch()
        
        lbl_footer = QLabel("Univerzální aplikace v2.0 • Powered by Winget & Gemini AI")
        lbl_footer.setStyleSheet(f"color: {COLORS['sub_text']}; font-size: 11px; margin-top: 20px;")
        lbl_footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(lbl_footer)