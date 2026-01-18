import sys
import os
import shutil
import tempfile
import random
import glob
from pathlib import Path

# Fixní název souboru, pokud by nějaký zbyl
INSTALLER_FILENAME = "UniversalApp_Setup.exe"

def perform_boot_checks():
    """
    Spustí kritické kontroly prostředí pro PyInstaller.
    Podle logiky verze 6.3
    """
    # 1. KRITICKÁ OPRAVA PRO UPDATE
    # Pokud stará verze nastavila _MEIPASS2 (vnucuje staré knihovny),
    # musíme to smazat.
    if "_MEIPASS2" in os.environ:
        del os.environ["_MEIPASS2"]

    # 2. Cleanup starých instalátorů (Hygiena)
    try:
        temp_dir = tempfile.gettempdir()
        installer_path = os.path.join(temp_dir, INSTALLER_FILENAME)
        if os.path.exists(installer_path):
            try: os.remove(installer_path)
            except: pass
    except: pass

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)