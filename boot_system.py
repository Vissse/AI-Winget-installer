import os
import tempfile
import time

# Název souboru instalátoru (musí být shodný s updater.py)
INSTALLER_FILENAME = "UniversalApp_Setup.exe"

def cleanup_installer():
    """
    Smaže stažený instalátor z Temp složky při startu aplikace.
    """
    try:
        temp_dir = tempfile.gettempdir()
        installer_path = os.path.join(temp_dir, INSTALLER_FILENAME)
        
        if os.path.exists(installer_path):
            try:
                # Zkusíme smazat. Pokud to nejde (ještě běží?), nevadí.
                os.remove(installer_path)
            except Exception:
                pass 
    except Exception:
        pass