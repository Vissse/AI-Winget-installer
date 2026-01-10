# config.py
import os
from pathlib import Path

# ZDE JE NYNÍ VERZE APLIKACE
CURRENT_VERSION = "4.3.32"

# --- NASTAVENÍ CESTY DO DOKUMENTŮ ---
# Tímto zajistíme, že se nastavení uloží do C:/Users/Uzivatel/Documents/AI_Winget_Installer/
# a neztratí se při aktualizaci nebo restartu.

try:
    # Získá cestu k dokumentům aktuálního uživatele
    _docs_dir = Path.home() / "Documents" / "AI_Winget_Installer"
    
    # Pokud složka neexistuje, vytvoříme ji
    _docs_dir.mkdir(parents=True, exist_ok=True)
    
    # Nastavíme cesty k souborům do této složky
    SETTINGS_FILE = str(_docs_dir / "user_settings.json")
    OUTPUT_FILE = str(_docs_dir / "install_apps.bat")
    
except Exception as e:
    # Záložní řešení, kdyby se nepovedlo získat cestu k dokumentům
    print(f"Chyba při nastavování cesty: {e}")
    SETTINGS_FILE = "user_settings.json"
    OUTPUT_FILE = "install_apps.bat"


# API a další konstanty
DEFAULT_API_KEY = "" 

COLORS = {
    "bg_main": "#1e1e1e",
    "bg_sidebar": "#252525",
    "fg": "#ffffff",
    "accent": "#4DA6FF",
    "accent_hover": "#6ebaff",
    "sidebar_hover": "#2c2c2c",
    "sidebar_active": "#363636",
    "success": "#3fb950",
    "success_hover": "#56d364",
    "danger": "#f85149",
    "danger_hover": "#ff7b72",
    "item_bg": "#2d2d2d",
    "item_hover": "#383838",
    "input_bg": "#3c3c3c",
    "sub_text": "#8b949e",
    "border": "#30363d"
}