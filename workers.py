import subprocess
import re
from PyQt6.QtCore import QThread, pyqtSignal

class WingetListWorker(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def run(self):
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            # -n 1 zrychlí výpis, ale pro list potřebujeme vše
            result = subprocess.run('winget list --accept-source-agreements', 
                                    capture_output=True, text=True, shell=True, 
                                    startupinfo=startupinfo, encoding='utf-8', errors='replace')
            
            lines = result.stdout.split('\n')
            apps = []
            start_parsing = False
            
            for line in lines:
                if line.startswith("Name") and "Id" in line:
                    start_parsing = True; continue
                if not start_parsing or "----" in line or not line.strip(): continue
                
                parts = re.split(r'\s{2,}', line.strip())
                if len(parts) >= 2:
                    name = parts[0]
                    app_id = parts[1]
                    if "Microsoft.Windows" not in app_id: 
                        apps.append({'name': name, 'id': app_id})
            
            apps.sort(key=lambda x: x['name'].lower())
            self.finished.emit(apps)
        except Exception as e:
            self.error.emit(str(e))

class UninstallWorker(QThread):
    log = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, app_id):
        super().__init__()
        self.app_id = app_id

    def run(self):
        self.log.emit(f"Spouštím odinstalaci: {self.app_id}")
        cmd = f'winget uninstall --id "{self.app_id}" --accept-source-agreements'
        
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   text=True, encoding='utf-8', errors='replace', startupinfo=startupinfo)
        
        for line in process.stdout:
            self.log.emit(line.strip())
            
        process.wait()
        self.finished.emit()