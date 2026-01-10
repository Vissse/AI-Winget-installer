# boot_system.py
import sys
import os
import shutil
import tempfile
import random
import ctypes
from pathlib import Path

def perform_boot_checks():
    """
    Spustí kritické kontroly prostředí pro PyInstaller.
    Řeší problém 'Failed to load Python DLL' čištěním proměnných prostředí.
    """
    # 1. FIX PRO PYINSTALLER UPDATE (BOOTLOADER FIX)
    # Odstraní 'jedovatou' proměnnou zděděnou od starého procesu
    if "_MEIPASS2" in os.environ:
        os.environ.pop("_MEIPASS2", None)

    # 2. SAFE BOOT (Záloha prostředí)
    # Pokud jsme v EXE, zálohujeme knihovny do Tempu pro případ nouze
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        try:
            current_mei = Path(sys._MEIPASS)
            safe_mei_path = Path(tempfile.gettempdir()) / f"AIWinget_Safe_MEI_{random.randint(1000, 99999)}"
            
            if not safe_mei_path.exists():
                shutil.copytree(current_mei, safe_mei_path, dirs_exist_ok=True)
                
            # Přidáme zálohu do PATH
            os.environ["PATH"] += os.pathsep + str(safe_mei_path)
        except Exception:
            pass

def resource_path(relative_path):
    """Získá absolutní cestu ke zdrojům (funguje pro dev i EXE)."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def is_admin():
    """Ověří, zda aplikace běží s právy správce."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False