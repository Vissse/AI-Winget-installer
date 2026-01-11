# config.py
import os
import json
from pathlib import Path

CURRENT_VERSION = "6.0"

try:
    _docs_dir = Path.home() / "Documents" / "AI_Winget_Installer"
    _docs_dir.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE = str(_docs_dir / "user_settings.json")
    OUTPUT_FILE = str(_docs_dir / "install_apps.bat")
except Exception:
    SETTINGS_FILE = "user_settings.json"
    OUTPUT_FILE = "install_apps.bat"

DEFAULT_API_KEY = "" 

# --- 1. DEFINICE TÉMAT ---
THEMES = {
    # PŘEJMENOVÁNO: Místo "Notion Light" -> "Light (Minimal)"
    "Light (Minimal)": {
        "bg_main": "#FFFFFF",
        "bg_sidebar": "#F7F7F7",
        "fg": "#37352F",
        "accent": "#2E7CE5",
        "accent_hover": "#1F6AD0",
        "sidebar_hover": "#EFEFEF",
        "sidebar_active": "#EBF5FF",
        "success": "#2D9D78",
        "success_hover": "#268C6A",
        "danger": "#DF5452",
        "danger_hover": "#C94A48",
        "item_bg": "#FFFFFF",
        "item_hover": "#F7F7F7",
        "input_bg": "#F0F2F5",
        "sub_text": "#787774",
        "border": "#E0E0E0"
    },
    "Dark (Default)": {
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
}

# --- 2. INICIALIZACE BAREV ---
# Změna výchozího tématu na nové jméno
COLORS = THEMES["Light (Minimal)"].copy()

try:
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Pokud měl uživatel uloženo staré jméno "Notion Light", přepneme ho na nové
            saved_theme = data.get("theme", "Light (Minimal)")
            if saved_theme == "Notion Light": saved_theme = "Light (Minimal)"
            
            if saved_theme in THEMES:
                COLORS.update(THEMES[saved_theme])
except Exception:
    pass