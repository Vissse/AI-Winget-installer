import os
import json
from pathlib import Path

CURRENT_VERSION = "7.4.8.2"

try:
    _docs_dir = Path.home() / "Documents" / "AI_Winget_Installer"
    _docs_dir.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE = str(_docs_dir / "user_settings.json")
    OUTPUT_FILE = str(_docs_dir / "install_apps.bat")
except Exception:
    SETTINGS_FILE = "user_settings.json"
    OUTPUT_FILE = "install_apps.bat"

# --- 1. DEFINICE TÉMAT ---
# Musí obsahovat všechny klíče, které používají nové PyQt views
THEMES = {
    "Dark (Default)": {
        "bg_main": "#1e1e1e",
        "bg_sidebar": "#252526",
        "fg": "#ffffff",
        "sub_text": "#888888",
        "input_bg": "#3c3c3c",
        "accent": "#007acc",       # VS Code Blue
        "accent_hover": "#1f8ad2",
        "danger": "#d83b01",
        "danger_hover": "#e84a1b", # PŘIDÁNO: Světlejší červená pro hover
        "success": "#107c10",
        "success_hover": "#138913",# PŘIDÁNO: Světlejší zelená pro hover
        "item_bg": "#2d2d30",
        "item_hover": "#3e3e42",
        "border": "#3e3e42"
    },
    "Light": {
        "bg_main": "#ffffff",
        "bg_sidebar": "#f3f3f3",
        "fg": "#000000",
        "sub_text": "#666666",
        "input_bg": "#ffffff",
        "accent": "#007acc",
        "accent_hover": "#005a9e",
        "danger": "#d83b01",
        "danger_hover": "#b03001", # PŘIDÁNO: Tmavší červená pro kontrast
        "success": "#107c10",
        "success_hover": "#0d6b0d",# PŘIDÁNO: Tmavší zelená pro kontrast
        "item_bg": "#ffffff",
        "item_hover": "#e1e1e1",
        "border": "#cccccc"
    }
}

# --- 2. NAČTENÍ AKTIVNÍHO TÉMATU ---
# Defaultně nastavíme Dark
COLORS = THEMES["Dark (Default)"].copy()

# Pokud existuje nastavení, pokusíme se načíst uložené téma
try:
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            saved_theme = data.get("theme", "Dark (Default)")
            
            # Fallback pro staré názvy témat
            if saved_theme == "Notion Light": saved_theme = "Light"
            
            if saved_theme in THEMES:
                COLORS = THEMES[saved_theme].copy()
except Exception:
    pass