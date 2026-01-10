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
    """
    # --- KRITICKÁ OPRAVA PRO UPDATE (Podle dokumentace PyInstaller) ---
    # Pokud stará verze nastavila _MEIPASS2 (vnucuje staré knihovny),
    # musíme to smazat, aby si nová verze načetla své vlastní, správné verze.
    # Toto řeší situace, kdy se bootloader chytí, ale Python by mohl být zmatený.
    if "_MEIPASS2" in os.environ:
        del os.environ["_MEIPASS2"]

    # 2. SAFE BOOT (Záloha prostředí - volitelné, pro jistotu)
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        try:
            current_mei = Path(sys._MEIPASS)
            safe_mei_path = Path(tempfile.gettempdir()) / f"AIWinget_Safe_MEI_{random.randint(1000, 99999)}"
            
            if not safe_mei_path.exists():
                shutil.copytree(current_mei, safe_mei_path, dirs_exist_ok=True)
                
            os.environ["PATH"] += os.pathsep + str(safe_mei_path)
        except Exception:
            pass

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False