# settings_manager.py
import json
import os
from config import SETTINGS_FILE

class SettingsManager:
    @staticmethod
    def load_settings():
        if not os.path.exists(SETTINGS_FILE):
            return {"api_key": ""}
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {"api_key": ""}

    @staticmethod
    def save_settings(data):
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            return True
        except:
            return False