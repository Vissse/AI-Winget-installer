# boot_system.py
import sys
import os
import shutil
import tempfile
import glob
from pathlib import Path
import ctypes

# Název souboru instalátoru, který budeme hledat v Downloads a mazat
INSTALLER_FILENAME = "WingetInstaller_Setup_Update.exe"

def cleanup_installer():
    """
    Smaže stažený instalátor ze složky Downloads, pokud tam zbyl z minula.
    """
    try:
        downloads_path = str(Path.home() / "Downloads")
        installer_path = os.path.join(downloads_path, INSTALLER_FILENAME)
        
        if os.path.exists(installer_path):
            try:
                os.remove(installer_path)
            except Exception:
                pass # Pokud je soubor zamčený, necháme ho být
    except Exception:
        pass

def cleanup_old_mei_folders():
    """
    Pokusí se smazat staré _MEI složky v Tempu (pozůstatky z doby, kdy byla appka OneFile).
    Tohle tu necháme, aby se uživatelům vyčistil disk po starých verzích.
    """
    try:
        temp_dir = tempfile.gettempdir()
        base_mei = os.path.join(temp_dir, "_MEI*")
        
        for mei_folder in glob.glob(base_mei):
            try:
                # V onedir režimu nic neběží z MEI, takže můžeme mazat všechno
                shutil.rmtree(mei_folder, ignore_errors=True)
            except Exception:
                pass
    except Exception:
        pass

def perform_boot_checks():
    """
    Spustí úklid při startu.
    """
    # 1. Smazání instalačního souboru z Downloads
    cleanup_installer()
    
    # 2. Úklid starých temp složek (údržba)
    cleanup_old_mei_folders()

def resource_path(relative_path):
    """
    Získá cestu k souboru (kompatibilní s --onedir).
    """
    try:
        if getattr(sys, 'frozen', False):
            # V onedir je base_path složka, kde leží .exe
            base_path = os.path.dirname(sys.executable)
        else:
            base_path = os.path.abspath(".")
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False