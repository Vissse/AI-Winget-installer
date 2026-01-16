import random
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QProgressBar, QFrame, QApplication)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPalette

from config import COLORS, CURRENT_VERSION

class SplashScreen(QWidget):
    # Signál, který pošleme do main.py, až se načítání dokončí
    finished = pyqtSignal()

    def __init__(self):
        super().__init__()
        # Nastavení okna: Bez rámečku, Vždy navrchu, Průhledné pozadí (pro zakulacené rohy)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.SplashScreen)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Hlavní layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10) # Okraj pro stín (pokud bys chtěl)
        
        # Kontejner (Vzhled okna)
        self.container = QFrame()
        self.container.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_main']};
                border: 2px solid {COLORS['accent']};
                border-radius: 12px;
            }}
        """)
        
        # Stín (volitelné, v PyQt složitější, zde řešíme borderem)
        
        inner_layout = QVBoxLayout(self.container)
        inner_layout.setContentsMargins(40, 50, 40, 40)
        
        # 1. Název Aplikace
        lbl_title = QLabel("AI Winget Installer")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_title.setStyleSheet(f"color: {COLORS['fg']}; font-size: 26px; font-weight: bold; border: none; font-family: 'Segoe UI';")
        inner_layout.addWidget(lbl_title)
        
        # 2. Verze
        lbl_ver = QLabel(f"Alpha version {CURRENT_VERSION}")
        lbl_ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_ver.setStyleSheet(f"color: {COLORS['accent']}; font-size: 13px; border: none; margin-bottom: 30px; font-family: 'Segoe UI';")
        inner_layout.addWidget(lbl_ver)
        
        # 3. Status Text (Načítání...)
        self.lbl_status = QLabel("Inicializace...")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setStyleSheet(f"color: {COLORS['sub_text']}; font-size: 11px; border: none; font-family: 'Segoe UI';")
        inner_layout.addWidget(self.lbl_status)
        
        # 4. Progress Bar
        self.progress = QProgressBar()
        self.progress.setFixedHeight(6)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet(f"""
            QProgressBar {{
                background-color: {COLORS['bg_sidebar']};
                border-radius: 3px;
                border: none;
            }}
            QProgressBar::chunk {{
                background-color: {COLORS['accent']};
                border-radius: 3px;
            }}
        """)
        inner_layout.addWidget(self.progress)
        
        layout.addWidget(self.container)
        
        # Nastavení velikosti a pozice
        self.resize(480, 300)
        self.center_on_screen()
        
        # Logika animace
        self.progress_val = 0
        self.loading_steps = ["Načítání konfigurace...", "Připojování k AI...", "Kontrola Winget...", "Načítání GUI...", "Hotovo!"]
        self.step_index = 0
        
        # Časovač pro animaci (náhrada za self.after z Tkinteru)
        self.timer = QTimer()
        self.timer.timeout.connect(self.animate)
        self.timer.start(30) # Každých 30ms

    def center_on_screen(self):
        screen = QApplication.primaryScreen().geometry()
        size = self.geometry()
        self.move(
            int((screen.width() - size.width()) / 2),
            int((screen.height() - size.height()) / 2)
        )

    def animate(self):
        if self.progress_val < 100:
            increment = random.randint(1, 4)
            self.progress_val += increment
            self.progress.setValue(self.progress_val)
            
            # Změna textu podle procent
            if self.progress_val > 20 and self.step_index == 0:
                self.step_index = 1
                self.lbl_status.setText(self.loading_steps[1])
            elif self.progress_val > 50 and self.step_index == 1:
                self.step_index = 2
                self.lbl_status.setText(self.loading_steps[2])
            elif self.progress_val > 80 and self.step_index == 2:
                self.step_index = 3
                self.lbl_status.setText(self.loading_steps[3])
        else:
            self.lbl_status.setText(self.loading_steps[4])
            self.timer.stop()
            # Počkáme chvilku na 100% a pak zavřeme
            QTimer.singleShot(500, self.finish_loading)

    def finish_loading(self):
        self.close()
        self.finished.emit() # Vyšleme signál do main.py