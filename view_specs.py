import sys
import os
import platform
import socket
import subprocess
import re
import csv
import io
import json
import datetime

from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QFrame, QStackedWidget, QScrollArea, QPushButton, 
                             QSizePolicy)
from PyQt6.QtCore import Qt, QSize, QVariantAnimation, QTimer, QRect, pyqtSignal
from PyQt6.QtGui import QColor, QIcon, QPixmap, QPainter, QPainterPath

# --- KONFIGURACE A BARVY ---
try:
    from config import COLORS, resource_path
except ImportError:
    COLORS = {
        'bg': '#121212', 'bg_sidebar': '#1e1e1e', 'item_bg': '#252525', 
        'item_hover': '#333333', 'accent': '#3498db', 'fg': '#ffffff', 
        'sub_text': '#aaaaaa', 'border': '#333333', 'success': '#2ecc71'
    }
    def resource_path(p): return p

# --- LOGIKA ZÍSKÁVÁNÍ DAT PC ---

def clean_disk_name(name):
    name = re.sub(r'\b(SSD|NVMe|HDD|USB)\b', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\b\d+\s?[GT]B?\b', '', name, flags=re.IGNORECASE)
    return " ".join(name.split())

def get_market_size(real_gb):
    if real_gb >= 900: return f"{round(real_gb / 1000)} TB"
    standards = [120, 128, 240, 250, 256, 480, 500, 512, 960, 1000]
    closest = min(standards, key=lambda x: abs(x - real_gb))
    if abs(closest - real_gb) / closest < 0.10:
        if closest in [480, 500]: return "512 GB"
        if closest in [240, 250]: return "256 GB"
        if closest == 120: return "128 GB"
        return f"{closest} GB"
    return f"{real_gb} GB"

def format_wmi_date(raw_date):
    raw_date = str(raw_date).strip()
    formatted = "Neznámé"
    if len(raw_date) >= 8 and raw_date[:8].isdigit():
        formatted = f"{raw_date[6:8]}.{raw_date[4:6]}.{raw_date[0:4]}"
    elif "/Date(" in raw_date:
        match = re.search(r'\d+', raw_date)
        if match:
            timestamp = int(match.group()) / 1000
            d = datetime.datetime.fromtimestamp(timestamp)
            formatted = d.strftime('%d.%m.%Y')
    return formatted

def get_gpu_vendor_from_id(pnp_id):
    """Rozklíčuje výrobce karty (Subvendor) z PNP ID stringu"""
    if not pnp_id: return ""
    
    # Hledáme část SUBSYS_xxxxxxxx. Výrobce jsou obvykle poslední 4 znaky.
    # Příklad: PCI\VEN_10DE&DEV_2882&SUBSYS_895E1043... -> 1043 je ASUS
    match = re.search(r'SUBSYS_([0-9A-F]{8})', pnp_id, re.IGNORECASE)
    if match:
        hex_str = match.group(1)
        subsys_id = hex_str[-4:].upper() # Vezmeme poslední 4 znaky (Little Endian)
        
        # Známé ID výrobců (PCI Vendor ID)
        vendors = {
            "1043": "ASUS",
            "1462": "MSI",
            "1458": "GIGABYTE",
            "3842": "EVGA",
            "19DA": "ZOTAC",
            "1682": "XFX",
            "1DA2": "SAPPHIRE",
            "1849": "ASRock",
            "196E": "PNY",
            "10DE": "NVIDIA", # Founders Edition / Reference
            "1002": "AMD",    # Reference
            "1028": "DELL",
            "103C": "HP",
            "17AA": "Lenovo"
        }
        return vendors.get(subsys_id, "")
    return ""

def get_pc_specs():
    os_name = f"Windows {platform.release()}"
    try:
        build = int(platform.version().split('.')[-1])
        os_base = "Windows 11" if build >= 22000 else "Windows 10"
        edition_raw = subprocess.check_output("wmic os get caption", shell=True).decode(errors='ignore')
        edition_text = edition_raw.split('\n')[1].strip()
        os_name = f"{os_base} Pro" if "Pro" in edition_text else (f"{os_base} Home" if "Home" in edition_text else os_base)
    except: pass

    specs = {
        "cpu": "Neznámý Procesor", 
        "cpu_details": {}, 
        "gpu": "Neznámá Grafika", 
        "gpu_details": {}, 
        "ram": "0 GB", 
        "ram_details": [], 
        "mobo": {
            "vendor": "", "product": "Neznámá Deska", "version": "", 
            "serial": "", "bios": ""
        },
        "storage": [], "os": os_name, "pc_name": socket.gethostname()
    }
    
    try:
        # --- CPU ---
        cmd_cpu = 'powershell "Get-CimInstance Win32_Processor | Select-Object Name, NumberOfCores, NumberOfLogicalProcessors, MaxClockSpeed, L2CacheSize, L3CacheSize, SocketDesignation, VirtualizationFirmwareEnabled | ConvertTo-Json"'
        try:
            cpu_output = subprocess.check_output(cmd_cpu, shell=True).decode(errors='ignore')
            if cpu_output.strip():
                cpu_data = json.loads(cpu_output)
                if isinstance(cpu_data, list): cpu_data = cpu_data[0]

                name = cpu_data.get("Name", "Neznámý Procesor").strip()
                cores = cpu_data.get("NumberOfCores", 0)
                threads = cpu_data.get("NumberOfLogicalProcessors", 0)
                speed_mhz = cpu_data.get("MaxClockSpeed", 0)
                speed_ghz = f"{speed_mhz / 1000:.1f} GHz" if speed_mhz else "N/A"
                l2_kb = cpu_data.get("L2CacheSize", 0); l2_mb = f"{l2_kb // 1024} MB" if l2_kb else "N/A"
                l3_kb = cpu_data.get("L3CacheSize", 0); l3_mb = f"{l3_kb // 1024} MB" if l3_kb else "N/A"
                socket_type = cpu_data.get("SocketDesignation", "Neznámý")
                virt = "Zapnuta" if cpu_data.get("VirtualizationFirmwareEnabled") else "Vypnuta"

                specs["cpu"] = name
                specs["cpu_details"] = { "cores": f"{cores} Jader / {threads} Vláken", "speed": speed_ghz, "l2": l2_mb, "l3": l3_mb, "socket": socket_type, "virt": virt }
            else:
                specs["cpu"] = subprocess.check_output("wmic cpu get name", shell=True).decode(errors='ignore').split('\n')[1].strip()
        except: specs["cpu"] = "Chyba načítání CPU"

        # --- GPU (S DETEKCÍ VÝROBCE "ASUS" ATD.) ---
        # Přidali jsme PNPDeviceID do dotazu
        cmd_gpu_basic = 'powershell "Get-CimInstance Win32_VideoController | Select-Object Name, DriverVersion, DriverDate, PNPDeviceID | ConvertTo-Json"'
        try:
            gpu_output = subprocess.check_output(cmd_gpu_basic, shell=True).decode(errors='ignore')
            
            # VRAM Logic
            vram_final_gb = "Neznámá"
            
            # 1. NVIDIA-SMI
            try:
                nvidia_size_cmd = "nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits"
                nvidia_size_out = subprocess.check_output(nvidia_size_cmd, shell=True).decode(errors='ignore').strip()
                if nvidia_size_out and nvidia_size_out.isdigit():
                    gb_val = int(nvidia_size_out) / 1024
                    vram_final_gb = f"{int(gb_val)} GB" if gb_val.is_integer() else f"{gb_val:.1f} GB"
            except: pass

            # 2. Registry
            if vram_final_gb == "Neznámá":
                try:
                    cmd_gpu_reg = 'powershell "Get-ItemProperty -Path \'HKLM:\\SYSTEM\\ControlSet001\\Control\\Class\\{4d36e968-e325-11ce-bfc1-08002be10318}\\*\' -ErrorAction SilentlyContinue | Where-Object { $_.\'HardwareInformation.QwMemorySize\' -ne $null } | Sort-Object \'HardwareInformation.QwMemorySize\' -Descending | Select-Object -First 1 -ExpandProperty \'HardwareInformation.QwMemorySize\'"'
                    reg_out = subprocess.check_output(cmd_gpu_reg, shell=True).decode(errors='ignore').strip()
                    if reg_out and reg_out.isdigit() and int(reg_out) > 0:
                        vram_final_gb = f"{round(int(reg_out) / (1024**3))} GB"
                except: pass

            if gpu_output.strip():
                gpu_data = json.loads(gpu_output)
                if isinstance(gpu_data, list): gpu_data = gpu_data[0]

                g_name = gpu_data.get("Name", "Neznámá Grafika")
                pnp_id = gpu_data.get("PNPDeviceID", "")
                
                # --- DETEKCE SUBVENDORA (ASUS, MSI...) ---
                subvendor = get_gpu_vendor_from_id(pnp_id)
                if subvendor and subvendor not in g_name.upper():
                    g_name = f"{subvendor} {g_name}"

                drv_ver = gpu_data.get("DriverVersion", "Neznámá")
                drv_date = format_wmi_date(gpu_data.get("DriverDate", ""))

                # 3. WMI Fallback
                if vram_final_gb == "Neznámá":
                    try:
                        cmd_wmi_ram = 'powershell "Get-CimInstance Win32_VideoController | Select-Object AdapterRAM | ConvertTo-Json"'
                        ram_out = json.loads(subprocess.check_output(cmd_wmi_ram, shell=True).decode(errors='ignore'))
                        if isinstance(ram_out, list): ram_out = ram_out[0]
                        wmi_bytes = ram_out.get("AdapterRAM", 0)
                        if wmi_bytes > 0: vram_final_gb = f"{round(wmi_bytes / (1024**3))} GB"
                    except: pass
                
                if ".0 GB" in vram_final_gb: vram_final_gb = vram_final_gb.replace(".0 GB", " GB")

                specs["gpu"] = g_name
                specs["gpu_details"] = { "vram": vram_final_gb, "driver_ver": drv_ver, "driver_date": drv_date }
            else:
                specs["gpu"] = subprocess.check_output("wmic path win32_VideoController get name", shell=True).decode(errors='ignore').split('\n')[1].strip()
        except: specs["gpu"] = "Chyba GPU"

        # --- Motherboard ---
        cmd_mb = 'powershell "Get-CimInstance Win32_BaseBoard | Select-Object Manufacturer, Product, Version, SerialNumber | ConvertTo-Json"'
        mb_data = json.loads(subprocess.check_output(cmd_mb, shell=True).decode(errors='ignore'))
        if isinstance(mb_data, list): mb_data = mb_data[0]
        specs["mobo"]["vendor"] = mb_data.get("Manufacturer", "").strip()
        prod = mb_data.get("Product", "").strip()
        specs["mobo"]["product"] = mb_data.get("Version", prod) if "Ltd" in prod else prod
        specs["mobo"]["version"] = mb_data.get("Version", "").strip()
        specs["mobo"]["serial"] = mb_data.get("SerialNumber", "").strip()

        # --- BIOS ---
        cmd_bios = 'powershell "Get-CimInstance Win32_BIOS | Select-Object SMBIOSBIOSVersion, ReleaseDate | ConvertTo-Json"'
        bios_data = json.loads(subprocess.check_output(cmd_bios, shell=True).decode(errors='ignore'))
        if isinstance(bios_data, list): bios_data = bios_data[0]
        bios_ver = bios_data.get("SMBIOSBIOSVersion", "")
        formatted_date = f" ({format_wmi_date(bios_data.get('ReleaseDate', ''))})"
        specs["mobo"]["bios"] = f"{bios_ver}{formatted_date}"
        
        # --- RAM ---
        ram_cmd = "wmic memorychip get capacity, speed, manufacturer, partnumber /format:csv"
        ram_raw = subprocess.check_output(ram_cmd, shell=True).decode(errors='ignore')
        f = io.StringIO(ram_raw.strip()); reader = csv.DictReader(f); total_ram = 0
        for row in reader:
            try:
                cap = int(row.get('Capacity', 0)); total_ram += cap
                specs["ram_details"].append(f"{row.get('Manufacturer', '').strip()} {row.get('PartNumber', '').strip()}\n{cap // (1024**3)} GB @ {row.get('Speed', 'Unknown')} MHz")
            except: continue
        specs["ram"] = f"{total_ram // (1024**3)} GB"

        # --- Storage ---
        ps_cmd = 'powershell "Get-PhysicalDisk | Select-Object FriendlyName, MediaType, BusType, SpindleSpeed, Size | ConvertTo-Json"'
        try:
            disks_raw = subprocess.check_output(ps_cmd, shell=True).decode(errors='ignore')
            disks_data = json.loads(disks_raw)
            if isinstance(disks_data, dict): disks_data = [disks_data] 

            for d in disks_data:
                name = d.get('FriendlyName', 'Unknown')
                media_type = d.get('MediaType', 'Unspecified')
                bus = d.get('BusType', 'Unknown')
                spindle = d.get('SpindleSpeed', 0)
                size_bytes = d.get('Size', 0)

                if media_type == 'Unspecified':
                    if spindle > 0: media_type = 'HDD'
                    elif 'HD' in name and 'SSD' not in name: media_type = 'HDD'
                    elif 'SSD' in name: media_type = 'SSD'

                if size_bytes:
                    real_gb = round(size_bytes / (1024**3))
                    specs["storage"].append({
                        "name": name,
                        "type": media_type,
                        "bus": "NVMe" if bus == "NVMe" else bus,
                        "real_size": f"{real_gb} GB",
                        "market_size": get_market_size(real_gb)
                    })
        except: pass

    except: pass
    return specs

# --- UI KOMPONENTY ---

class MoboRow(QFrame):
    def __init__(self, title, value):
        super().__init__()
        self.setStyleSheet(f"border-bottom: 1px solid {COLORS['border']}; background: transparent;")
        l = QHBoxLayout(self); l.setContentsMargins(10, 8, 15, 8); l.setSpacing(20)
        t_lbl = QLabel(str(title).upper()); t_lbl.setFixedWidth(180) 
        t_lbl.setStyleSheet(f"color: {COLORS['accent']}; font-size: 10px; font-weight: bold; border: none;")
        v_lbl = QLabel(str(value)); v_lbl.setWordWrap(True)
        v_lbl.setStyleSheet(f"color: {COLORS['fg']}; font-size: 13px; border: none;")
        l.addWidget(t_lbl); l.addWidget(v_lbl)

class DiskRow(QFrame):
    def __init__(self, disk_data, col_widths, parent_page):
        super().__init__()
        self.parent_page = parent_page; self.data = disk_data
        self.setCursor(Qt.CursorShape.PointingHandCursor); self.setFixedHeight(45)
        clean_name = clean_disk_name(self.data['name'])
        self.copy_text = f"{clean_name} {self.data['type']} {self.data['market_size']}"
        self.layout = QHBoxLayout(self); self.layout.setContentsMargins(15, 0, 15, 0); self.layout.setSpacing(0)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.add_column(clean_name, col_widths[0], f"color: {COLORS['fg']}; font-weight: 500;")
        self.add_column(self.data['type'], col_widths[1], f"color: {COLORS['sub_text']};")
        self.add_column(self.data['bus'], col_widths[2], f"color: {COLORS['sub_text']};")
        self.add_column(self.data['market_size'], col_widths[3], f"color: {COLORS['fg']}; font-weight: bold;")
        self.add_column(self.data['real_size'], col_widths[4], f"color: {COLORS['sub_text']};")

    def add_column(self, text, width, style):
        lbl = QLabel(text); lbl.setFixedWidth(width); lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        lbl.setStyleSheet(f"background: transparent; border: none; {style}"); self.layout.addWidget(lbl)
    def enterEvent(self, event): self.setStyleSheet(f"background-color: {COLORS['item_hover']}; border-radius: 4px;")
    def leaveEvent(self, event): self.setStyleSheet("background-color: transparent;")
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            QApplication.clipboard().setText(self.copy_text); self.parent_page.show_copy_notification()

class AnimatedNavItem(QFrame):
    clicked = pyqtSignal(int)
    def __init__(self, text, index, parent=None):
        super().__init__(parent)
        self.index = index; self.active = False; self.setCursor(Qt.CursorShape.PointingHandCursor); self.setFixedHeight(45)
        self._bg_color = QColor("transparent"); self._bar_height_factor = 0.0
        layout = QHBoxLayout(self); layout.setContentsMargins(15, 0, 10, 0)
        self.label = QLabel(text); self.label.setStyleSheet(f"color: {COLORS['sub_text']}; font-size: 13px; font-weight: 500; border: none; background: transparent;")
        layout.addWidget(self.label)
        self.anim = QVariantAnimation(self); self.anim.setDuration(250); self.anim.setStartValue(0.0); self.anim.setEndValue(1.0)
        self.anim.valueChanged.connect(self._animate_step)
    def set_active(self, active): self.active = active; self._animate_step(1.0 if active else 0.0)
    def _animate_step(self, val):
        if not self.active:
            target_bg = QColor(COLORS['item_hover'])
            self._bg_color = QColor(target_bg.red(), target_bg.green(), target_bg.blue(), int(255 * val))
            self._bar_height_factor = val
            self.label.setStyleSheet(f"color: {COLORS['fg'] if val > 0.5 else COLORS['sub_text']}; font-size: 13px; font-weight: 500; border: none; background: transparent;")
        else:
            self._bg_color = QColor(COLORS['item_bg']); self._bar_height_factor = 1.0
            self.label.setStyleSheet(f"color: #ffffff; font-size: 13px; border: none; background: transparent;")
        self.update()
    def enterEvent(self, event): 
        if not self.active: self.anim.setDirection(QVariantAnimation.Direction.Forward); self.anim.start()
    def leaveEvent(self, event): 
        if not self.active: self.anim.setDirection(QVariantAnimation.Direction.Backward); self.anim.start()
    def mousePressEvent(self, event): self.clicked.emit(self.index)
    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(1, 1, -1, -1); radius = 8
        if self._bg_color.alpha() > 0:
            p.setBrush(self._bg_color); p.setPen(Qt.PenStyle.NoPen); p.drawRoundedRect(rect, radius, radius)
        if self._bar_height_factor > 0:
            p.setBrush(QColor(COLORS['accent'])); p.setPen(Qt.PenStyle.NoPen)
            h = rect.height() * self._bar_height_factor; y = rect.y() + (rect.height() - h) / 2
            path = QPainterPath(); path.addRoundedRect(rect.x(), rect.y(), rect.width(), rect.height(), radius, radius)
            p.setClipPath(path); p.drawRect(QRect(0, int(y), 4, int(h))); p.setClipping(False)

class AnimatedCard(QFrame):
    def __init__(self, title, value):
        super().__init__()
        self.setFixedHeight(85)
        self._bg_color = QColor(COLORS['item_bg']); self._bar_height_factor = 0.0 
        layout = QVBoxLayout(self); layout.setContentsMargins(22, 12, 15, 12)
        self.t_lbl = QLabel(title.upper()); self.t_lbl.setStyleSheet(f"color: {COLORS['accent']}; font-size: 10px; font-weight: bold; background:transparent;")
        self.v_lbl = QLabel(value); self.v_lbl.setWordWrap(True); self.v_lbl.setStyleSheet(f"color: {COLORS['fg']}; font-size: 14px; font-weight: 500; background:transparent;")
        layout.addWidget(self.t_lbl); layout.addWidget(self.v_lbl)
        self.anim = QVariantAnimation(self); self.anim.setDuration(250); self.anim.setStartValue(0.0); self.anim.setEndValue(1.0)
        self.anim.valueChanged.connect(self._animate_step)
    def _animate_step(self, val):
        start_bg = QColor(COLORS['item_bg']); end_bg = QColor(COLORS['item_hover'])
        r = start_bg.red() + (end_bg.red() - start_bg.red()) * val
        g = start_bg.green() + (end_bg.green() - start_bg.green()) * val
        b = start_bg.blue() + (end_bg.blue() - start_bg.blue()) * val
        self._bg_color = QColor(int(r), int(g), int(b)); self._bar_height_factor = val; self.update()
    def enterEvent(self, event): self.anim.setDirection(QVariantAnimation.Direction.Forward); self.anim.start()
    def leaveEvent(self, event): self.anim.setDirection(QVariantAnimation.Direction.Backward); self.anim.start()
    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect(); radius = 8
        p.setBrush(self._bg_color); p.setPen(Qt.PenStyle.NoPen); p.drawRoundedRect(rect, radius, radius)
        if self._bar_height_factor > 0:
            p.setBrush(QColor(COLORS['accent'])); h = rect.height() * self._bar_height_factor; y = rect.y() + (rect.height() - h) / 2
            path = QPainterPath(); path.addRoundedRect(0, 0, rect.width(), rect.height(), radius, radius)
            p.setClipPath(path); p.drawRect(QRect(0, int(y), 4, int(h))); p.setClipping(False)

class MiniToast(QLabel):
    def __init__(self, parent):
        super().__init__("Zkopírováno!", parent)
        self.setStyleSheet(f"background: {COLORS['accent']}; color: white; padding: 5px 15px; border-radius: 4px; font-weight: bold;")
        self.adjustSize(); self.hide()

class InfoHeaderCard(QFrame):
    def __init__(self, icon_name, title, value):
        super().__init__()
        # ZMĚNA 1: Průhledné pozadí a žádný rámeček (odstraněno border: 1px...)
        self.setStyleSheet("background-color: transparent; border: none;")
        
        l = QHBoxLayout(self)
        # Upravené odsazení, aby to bez rámečku nebylo příliš "rozplizlé"
        l.setContentsMargins(5, 8, 15, 8) 
        
        icon_lbl = QLabel()
        path = resource_path(f"images/{icon_name}")
        if os.path.exists(path):
            pix = QPixmap(path).scaled(22, 22, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            p = QPainter(pix)
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
            
            # ZMĚNA 2: Barva ikonky. 
            # Původně: COLORS['sub_text'] (šedá). 
            # Nově: COLORS['fg'] (bílá - stejná jako text "Windows 11").
            # Pokud chcete modrou, dejte sem: COLORS['accent']
            p.fillRect(pix.rect(), QColor(COLORS['fg'])) 
            
            p.end()
            icon_lbl.setPixmap(pix)
        l.addWidget(icon_lbl)
        
        v_l = QVBoxLayout()
        v_l.setSpacing(0)
        
        # Nadpis (např. OPERAČNÍ SYSTÉM)
        t = QLabel(title.upper())
        t.setStyleSheet(f"color: {COLORS['sub_text']}; font-size: 9px; font-weight: bold; border: none;")
        
        # Hodnota (např. Windows 11 Pro)
        v = QLabel(value)
        v.setStyleSheet(f"color: {COLORS['fg']}; font-size: 13px; font-weight: bold; border: none;")
        
        v_l.addWidget(t)
        v_l.addWidget(v)
        l.addLayout(v_l)

# --- HLAVNÍ STRÁNKA ---

class SpecsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.specs = get_pc_specs()
        self.nav_items = []
        self.init_ui()
        self.toast = MiniToast(self)

    def show_copy_notification(self, text="Zkopírováno!"):
        self.toast.setText(text)
        self.toast.adjustSize()
        self.toast.move((self.width() - self.toast.width()) // 2, 20)
        self.toast.show(); self.toast.raise_()
        QTimer.singleShot(1500, self.toast.hide)

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(35, 30, 35, 30); main_layout.setSpacing(25)

        # Header
        header_row = QHBoxLayout()
        header_lbl = QLabel("Specifikace Počítače")
        header_lbl.setStyleSheet(f"font-size: 26px; font-weight: bold; color: {COLORS['fg']};")
        
        header_row.addWidget(header_lbl); header_row.addStretch()
        main_layout.addLayout(header_row)

        top_bar = QHBoxLayout()
        top_bar.addWidget(InfoHeaderCard("desktop-thin.png", "Název zařízení", self.specs['pc_name']))
        top_bar.addWidget(InfoHeaderCard("windows-logo-thin.png", "Operační systém", self.specs['os']))
        top_bar.addWidget(InfoHeaderCard("circuitry-thin.png", "Architektura", platform.machine()))
        top_bar.addStretch(); main_layout.addLayout(top_bar)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine); separator.setStyleSheet(f"background-color: {COLORS['border']}; min-height: 1px; max-height: 1px; border: none;")
        main_layout.addWidget(separator)

        content_layout = QHBoxLayout(); content_layout.setSpacing(25)

        self.sidebar_frame = QFrame(); self.sidebar_frame.setFixedWidth(210)
        self.sidebar_frame.setStyleSheet(f"QFrame {{ background-color: {COLORS['bg_sidebar']}; border-radius: 12px; border: none; }}")
        sidebar_layout = QVBoxLayout(self.sidebar_frame); sidebar_layout.setContentsMargins(10, 15, 10, 15); sidebar_layout.setSpacing(5)

        sections = ["Stručný přehled", "Procesor", "Základní deska", "Grafická karta", "Paměť", "Úložiště"]
        for i, name in enumerate(sections):
            item = AnimatedNavItem(name, i, self)
            item.clicked.connect(self.display_tab)
            sidebar_layout.addWidget(item); self.nav_items.append(item)
        
        sidebar_outer = QVBoxLayout(); sidebar_outer.addWidget(self.sidebar_frame); sidebar_outer.addStretch() 
        content_layout.addLayout(sidebar_outer)

        self.stack = QStackedWidget()
        self.stack.addWidget(self.create_summary_page())
        self.stack.addWidget(self.create_cpu_page())
        self.stack.addWidget(self.create_mobo_page())
        self.stack.addWidget(self.create_gpu_page())
        self.stack.addWidget(self.create_ram_page())
        self.stack.addWidget(self.create_disk_page())
        content_layout.addWidget(self.stack)

        main_layout.addLayout(content_layout)
        self.display_tab(0)

    def display_tab(self, idx):
        if idx == 2:
            w = self.stack.widget(2)
            self.stack.removeWidget(w)
            self.stack.insertWidget(2, self.create_mobo_page())
        self.stack.setCurrentIndex(idx)
        for i, item in enumerate(self.nav_items): item.set_active(i == idx)

    def create_mobo_page(self):
        m = self.specs['mobo']
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        content = QWidget()
        l = QVBoxLayout(content); l.setContentsMargins(0, 0, 10, 0); l.setSpacing(0)
        
        h_cont = QHBoxLayout(); h_cont.setContentsMargins(0,0,0,10)
        lbl_info = QLabel("ZÁKLADNÍ ÚDAJE"); lbl_info.setStyleSheet(f"color: {COLORS['sub_text']}; font-size: 11px; font-weight: bold;")
        h_cont.addWidget(lbl_info); h_cont.addStretch()
        l.addLayout(h_cont)
        
        l.addWidget(MoboRow("Výrobce", m['vendor']))
        l.addWidget(MoboRow("Model", m['product']))
        l.addWidget(MoboRow("BIOS Verze", m['bios']))
        l.addWidget(MoboRow("Sériové číslo", m['serial']))
        
        l.addStretch(); scroll.setWidget(content)
        return scroll

    def create_cpu_page(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        content = QWidget()
        l = QVBoxLayout(content); l.setContentsMargins(0, 0, 10, 0); l.setSpacing(0)

        h_cont = QHBoxLayout(); h_cont.setContentsMargins(0,0,0,10)
        lbl_info = QLabel("PROCESOR"); lbl_info.setStyleSheet(f"color: {COLORS['sub_text']}; font-size: 11px; font-weight: bold;")
        h_cont.addWidget(lbl_info); h_cont.addStretch()
        l.addLayout(h_cont)
        
        details = self.specs.get("cpu_details", {})
        l.addWidget(MoboRow("Model", self.specs['cpu']))
        
        if details:
            l.addWidget(MoboRow("Jádra / Vlákna", details.get('cores', 'N/A')))
            l.addWidget(MoboRow("Frekvence", details.get('speed', 'N/A')))
            l.addWidget(MoboRow("L2 Cache", details.get('l2', 'N/A')))
            l.addWidget(MoboRow("L3 Cache", details.get('l3', 'N/A')))
            l.addWidget(MoboRow("Socket", details.get('socket', 'N/A')))
            l.addWidget(MoboRow("Virtualizace", details.get('virt', 'N/A')))
        else:
            l.addWidget(MoboRow("Architektura", platform.machine()))
            
        l.addStretch(); scroll.setWidget(content)
        return scroll

    def create_gpu_page(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        content = QWidget()
        l = QVBoxLayout(content); l.setContentsMargins(0, 0, 10, 0); l.setSpacing(0)

        h_cont = QHBoxLayout(); h_cont.setContentsMargins(0,0,0,10)
        lbl_info = QLabel("GRAFICKÁ KARTA"); lbl_info.setStyleSheet(f"color: {COLORS['sub_text']}; font-size: 11px; font-weight: bold;")
        h_cont.addWidget(lbl_info); h_cont.addStretch()
        l.addLayout(h_cont)
        
        details = self.specs.get("gpu_details", {})
        l.addWidget(MoboRow("Model", self.specs['gpu']))

        if details:
            l.addWidget(MoboRow("Video Paměť (VRAM)", details.get('vram', 'N/A')))
            l.addWidget(MoboRow("Verze Ovladače", details.get('driver_ver', 'N/A')))
            l.addWidget(MoboRow("Datum Ovladače", details.get('driver_date', 'N/A')))
        
        l.addStretch(); scroll.setWidget(content)
        return scroll

    def create_summary_page(self):
        page = QWidget(); l = QVBoxLayout(page); l.setContentsMargins(0,0,0,0); l.setSpacing(12)
        l.addWidget(AnimatedCard("Procesor", self.specs['cpu']))
        
        gpu_label = self.specs['gpu']
        vram = self.specs.get('gpu_details', {}).get('vram', '')
        if vram and vram != "Neznámá":
            gpu_label += f" {vram}"
            
        l.addWidget(AnimatedCard("Grafická karta", gpu_label))
        l.addWidget(AnimatedCard("Základní deska", f"{self.specs['mobo']['vendor']} {self.specs['mobo']['product']}"))
        l.addWidget(AnimatedCard("Paměť RAM", self.specs['ram']))
        l.addStretch(); return page

    def create_ram_page(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        content = QWidget()
        l = QVBoxLayout(content); l.setContentsMargins(0, 0, 10, 0); l.setSpacing(0)

        h_cont = QHBoxLayout(); h_cont.setContentsMargins(0,0,0,10)
        lbl_info = QLabel("PAMĚŤ (RAM)"); lbl_info.setStyleSheet(f"color: {COLORS['sub_text']}; font-size: 11px; font-weight: bold;")
        h_cont.addWidget(lbl_info); h_cont.addStretch()
        l.addLayout(h_cont)

        l.addWidget(MoboRow("Celková kapacita", self.specs['ram']))
        
        for i, det in enumerate(self.specs['ram_details']):
            l.addWidget(MoboRow(f"Slot {i+1}", det))

        l.addStretch(); scroll.setWidget(content)
        return scroll

    def create_disk_page(self):
        page = QWidget(); l = QVBoxLayout(page); l.setContentsMargins(0, 0, 0, 0); l.setSpacing(5)
        col_widths = [250, 80, 80, 90, 90] 
        head = QFrame(); head.setStyleSheet(f"background: {COLORS['item_bg']}; border-radius: 4px;")
        h_lay = QHBoxLayout(head); h_lay.setContentsMargins(15, 8, 15, 8); h_lay.setSpacing(0); h_lay.setAlignment(Qt.AlignmentFlag.AlignLeft)
        titles = ["NÁZEV DISKU", "TYP", "SBĚRNICE", "VELIKOST", "REÁLNÁ"]
        for i, t in enumerate(titles):
            lbl = QLabel(t); lbl.setFixedWidth(col_widths[i]); lbl.setStyleSheet(f"color: {COLORS['fg']}; font-size: 9px; font-weight: bold; border: none;")
            h_lay.addWidget(lbl)
        l.addWidget(head)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setStyleSheet("background: transparent; border: none;")
        cont = QWidget(); c_lay = QVBoxLayout(cont); c_lay.setSpacing(2); c_lay.setContentsMargins(0, 5, 0, 0); c_lay.setAlignment(Qt.AlignmentFlag.AlignTop)
        for d in self.specs['storage']: c_lay.addWidget(DiskRow(d, col_widths, self))
        c_lay.addStretch(); scroll.setWidget(cont); l.addWidget(scroll)
        return page

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = SpecsPage()
    w.resize(900, 600)
    w.setStyleSheet(f"background-color: {COLORS['bg']};")
    w.show()
    sys.exit(app.exec())