import platform
import socket
import sys
import os
import subprocess
import winreg
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QFrame, QScrollArea, QSizePolicy)
from PyQt6.QtCore import Qt
from config import COLORS

# --- LOGIKA ZÍSKÁVÁNÍ DAT ---

def get_windows_product_name():
    try:
        key_path = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
            product_name, _ = winreg.QueryValueEx(key, "ProductName")
        ver = sys.getwindowsversion()
        if ver.major == 10 and ver.build >= 22000 and "Windows 10" in product_name:
            product_name = product_name.replace("Windows 10", "Windows 11")
        return product_name
    except:
        return f"Windows {platform.release()}"

def run_wmic_command(command):
    try:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        result = subprocess.run(command, capture_output=True, text=True, shell=True, startupinfo=startupinfo, encoding='cp852', errors='ignore')
        if not result.stdout.strip():
             # Fallback na utf-8
             result = subprocess.run(command, capture_output=True, text=True, shell=True, startupinfo=startupinfo, encoding='utf-8', errors='ignore')
        return result.stdout
    except Exception: return ""

def clean_hw_string(text):
    if not text: return "Neznámé"
    # Odstraní více mezer a stripne
    return " ".join(text.split())

def get_pc_specs():
    specs = {
        "cpu": "Neznámý procesor", 
        "gpu": "Neznámá grafika", 
        "ram": "Neznámá paměť", 
        "mobo": "Neznámá deska"
    }
    
    try:
        # 1. CPU
        raw_cpu = run_wmic_command("wmic cpu get name")
        for line in raw_cpu.split('\n'):
            if line.strip() and "Name" not in line:
                specs["cpu"] = clean_hw_string(line)
                break

        # 2. GPU
        raw_gpu = run_wmic_command("wmic path win32_VideoController get name")
        gpus = []
        for line in raw_gpu.split('\n'):
            if line.strip() and "Name" not in line: 
                gpus.append(clean_hw_string(line))
        
        selected_gpu = gpus[0] if gpus else "Standardní grafický adaptér"
        # Priorita dedikované grafiky
        for g in gpus:
            if any(x in g.upper() for x in ["NVIDIA", "AMD", "RTX", "GTX", "RADEON"]): 
                selected_gpu = g
                break
        specs["gpu"] = selected_gpu

        # 3. ZÁKLADNÍ DESKA
        manuf = run_wmic_command("wmic baseboard get Manufacturer")
        prod = run_wmic_command("wmic baseboard get Product")
        
        m_val = next((l.strip() for l in manuf.split('\n') if l.strip() and "Manufacturer" not in l), "MB")
        p_val = next((l.strip() for l in prod.split('\n') if l.strip() and "Product" not in l), "")
        
        specs["mobo"] = clean_hw_string(f"{m_val} {p_val}")

        # 4. RAM (Detailní info: Výrobce, Model, Kapacita, Rychlost)
        # Příkaz získá více informací
        raw_mem = run_wmic_command("wmic memorychip get Manufacturer, Capacity, Speed, PartNumber")
        
        total_bytes = 0
        speeds = set()
        manufacturers = set()
        
        # Parsování řádek po řádku
        # WMIC výstup je formátován do sloupců, ale Python split() si s tím poradí
        lines = raw_mem.strip().split('\n')
        
        for line in lines:
            if "Capacity" in line or not line.strip(): 
                continue
                
            parts = line.split()
            # Hledáme čísla pro Capacity a Speed, zbytek může být text
            
            # Kapacita je obvykle velmi velké číslo
            cap = 0
            spd = 0
            
            # Jednoduchá heuristika pro extrakci dat z řádku
            for part in parts:
                if part.isdigit():
                    val = int(part)
                    if val > 100000000: # Pravděpodobně kapacita v bajtech
                        cap = val
                    elif 100 < val < 10000: # Pravděpodobně frekvence v MHz
                        spd = val
                else:
                    # Pokud to není číslo a není to "Unknown" nebo "0000", je to asi výrobce/partnumber
                    if len(part) > 2 and "Unknown" not in part and "0000" not in part:
                        manufacturers.add(part)

            if cap > 0:
                total_bytes += cap
            if spd > 0:
                speeds.add(spd)

        # Výpočet GB
        total_gb = round(total_bytes / (1024**3))
        
        # Sestavení řetězce
        if total_gb > 0:
            speed_str = f"{max(speeds)} MHz" if speeds else ""
            manuf_str = " ".join(list(manufacturers)[:2]) # Vezmeme max 2 slova výrobce, ať to není dlouhé
            
            # Finální formát: "32 GB Kingston Fury (3200 MHz)"
            ram_info = f"{total_gb} GB"
            if manuf_str:
                ram_info += f" {manuf_str}"
            if speed_str:
                ram_info += f" ({speed_str})"
            
            specs["ram"] = ram_info
        else:
            # Fallback pokud detailní sken selže
            specs["ram"] = "Neznámá paměť (Zkuste spustit jako Admin)"

    except Exception as e: 
        print(f"HW Error: {e}")
        pass
        
    return specs

# --- WIDGETY ---

class InfoCard(QFrame):
    """Horní karty (OS, PC Name)"""
    def __init__(self, icon, title, value):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        self.setStyleSheet(f"QFrame {{ background-color: {COLORS['item_bg']}; border-radius: 6px; border: 1px solid {COLORS['border']}; }}")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 10, 20, 10) 
        layout.setSpacing(15)
        
        lbl_icon = QLabel(icon)
        lbl_icon.setStyleSheet("font-size: 20px; background: transparent; border: none;")
        layout.addWidget(lbl_icon)
        
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(f"color: {COLORS['sub_text']}; font-size: 10px; font-weight: bold; background: transparent; border: none;")
        lbl_value = QLabel(value)
        lbl_value.setStyleSheet("color: white; font-size: 13px; font-weight: bold; background: transparent; border: none;")
        
        text_layout.addWidget(lbl_title)
        text_layout.addWidget(lbl_value)
        layout.addLayout(text_layout)

class HardwareDetailWidget(QWidget):
    """
    Detailní widget pro hardware.
    BEZ IKONY, pouze texty pod sebou.
    """
    def __init__(self, label, value):
        super().__init__()
        # Jemné pozadí a rámeček
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS['item_bg']};
                border-radius: 6px;
                border-bottom: 2px solid {COLORS['border']};
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(5)
        
        # Nadpis (Typ komponenty) - Menší, barevný
        lbl_label = QLabel(label)
        lbl_label.setStyleSheet(f"""
            color: {COLORS['accent']}; 
            font-size: 11px; 
            font-weight: bold; 
            text-transform: uppercase; 
            background: transparent; 
            border: none;
        """)
        
        # Hodnota (Název HW) - Větší, bílá
        lbl_val = QLabel(value)
        lbl_val.setWordWrap(True)
        lbl_val.setStyleSheet("""
            color: white; 
            font-size: 16px; 
            font-weight: 500; 
            background: transparent; 
            border: none;
        """)
        
        layout.addWidget(lbl_label)
        layout.addWidget(lbl_val)

# --- HLAVNÍ STRÁNKA SPECIFIKACÍ ---

class SpecsPage(QWidget):
    def __init__(self):
        super().__init__()
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setSpacing(30)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Header
        lbl_head = QLabel("Specifikace Počítače")
        lbl_head.setStyleSheet("font-size: 28px; font-weight: bold; color: white;")
        main_layout.addWidget(lbl_head)
        
        # 1. Řádek: Systémové info (Zůstává v řadě nahoře)
        info_layout = QHBoxLayout()
        info_layout.setSpacing(15)
        info_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        try:
            pc_name = socket.gethostname()
            os_ver = get_windows_product_name()
            arch = platform.machine()
        except:
            pc_name, os_ver, arch = "Neznámé", "Windows", "x64"

        info_layout.addWidget(InfoCard("🖥️", "NÁZEV ZAŘÍZENÍ", pc_name))
        info_layout.addWidget(InfoCard("🪟", "OPERAČNÍ SYSTÉM", os_ver))
        info_layout.addWidget(InfoCard("⚙️", "ARCHITEKTURA", arch))
        info_layout.addStretch()
        
        main_layout.addLayout(info_layout)
        
        # Oddělovač
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background-color: {COLORS['border']}; margin-top: 10px; margin-bottom: 10px;")
        main_layout.addWidget(sep)

        # 2. Seznam Hardwaru (VERTIKÁLNĚ)
        lbl_hw = QLabel("HARDWARE KOMPONENTY")
        lbl_hw.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {COLORS['sub_text']}; margin-bottom: 10px;")
        main_layout.addWidget(lbl_hw)
        
        specs = get_pc_specs()
        
        # Použijeme QVBoxLayout místo Gridu, aby byly pod sebou
        hw_layout = QVBoxLayout()
        hw_layout.setSpacing(15)
        
        hw_layout.addWidget(HardwareDetailWidget("Procesor (CPU)", specs['cpu']))
        hw_layout.addWidget(HardwareDetailWidget("Grafická karta (GPU)", specs['gpu']))
        hw_layout.addWidget(HardwareDetailWidget("Operační paměť (RAM)", specs['ram']))
        hw_layout.addWidget(HardwareDetailWidget("Základní deska", specs['mobo']))
        
        main_layout.addLayout(hw_layout)
        main_layout.addStretch()