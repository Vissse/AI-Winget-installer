# boot_system.py
import sys
import os
import shutil
import tempfile
import random
import ctypes
import glob
from pathlib import Path

def cleanup_old_mei_folders():
    """
    Pokusí se smazat staré _MEI složky v Tempu, které tam zůstaly po předchozích updatech.
    Maže jen ty, které nejsou aktuálně používané (nejsou zamčené).
    """
    try:
        temp_dir = tempfile.gettempdir()
        base_mei = os.path.join(temp_dir, "_MEI*")
        
        # Zjistíme naši aktuální složku (pokud běžíme v exe), abychom nesmazali sami sebe
        current_mei = None
        if hasattr(sys, '_MEIPASS'):
            current_mei = sys._MEIPASS

        for mei_folder in glob.glob(base_mei):
            # Pokud je to naše aktuální složka, ignorujeme ji
            if current_mei and os.path.abspath(mei_folder) == os.path.abspath(current_mei):
                continue

            # Pokusíme se složku smazat
            try:
                shutil.rmtree(mei_folder, ignore_errors=True)
            except Exception:
                # Pokud to nejde smazat (někdo ji používá), nevadí, necháme ji být
                pass
    except Exception:
        pass


def perform_boot_checks():
    """
    Spustí kritické kontroly prostředí.
    """
    # 1. Úklid starého nepořádku
    cleanup_old_mei_folders()

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