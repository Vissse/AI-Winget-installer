import tkinter as tk
import threading
import requests
import json
from io import BytesIO
from PIL import Image, ImageTk
from urllib.parse import urlparse
from config import COLORS

# --- WINGET.RUN API ---
class WingetRunAPI:
    BASE_URL = "https://api.winget.run/v2/packages"

    @staticmethod
    def search(query, limit=5):
        results = []
        try:
            # 1. PARAMETRY - 'ensureContains' je klíčové pro správné výsledky
            params = {
                'query': query,
                'take': limit,
                'ensureContains': 'true' 
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            print(f"DEBUG API: Volám URL: {WingetRunAPI.BASE_URL} s parametry {params}")
            response = requests.get(WingetRunAPI.BASE_URL, params=params, headers=headers, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                packages = []

                # Bezpečné získání seznamu balíčků
                if isinstance(data, dict):
                    packages = data.get('Packages', [])
                elif isinstance(data, list):
                    packages = data
                
                print(f"DEBUG API: Nalezeno {len(packages)} balíčků.")

                for pkg in packages:
                    if not isinstance(pkg, dict): continue

                    # 1. Získání ID (Kořenový atribut 'Id' nebo 'PackageIdentifier')
                    pkg_id = pkg.get('Id') or pkg.get('PackageIdentifier')
                    if not pkg_id: continue

                    # 2. Načtení 'Latest' objektu (Klíčové pro metadata)
                    latest = pkg.get('Latest', {})
                    if not isinstance(latest, dict): latest = {}

                    # 3. Získání Názvu (Priorita: Latest.Name -> Root.Name -> ID)
                    name = latest.get('Name') or pkg.get('Name') or pkg_id

                    # 4. Získání Verze 
                    # Versions je pole stringů ['1.0', '2.0']. Latest verze je buď v 'Latest' objektu nebo první v poli.
                    version = "Latest"
                    versions_list = pkg.get('Versions', [])
                    if isinstance(versions_list, list) and len(versions_list) > 0:
                        version = versions_list[0] # První je obvykle nejnovější
                    
                    # 5. Získání Ikony (Hledáme všude)
                    icon_url = latest.get('IconUrl') or pkg.get('IconUrl') or pkg.get('Logo')

                    # 6. Další metadata (Tags, UpdatedAt)
                    # Tags jsou v Latest jako pole stringů
                    tags = latest.get('Tags', [])
                    tags_str = ", ".join(tags[:3]) if tags else "" # Vezmeme první 3 tagy
                    
                    # UpdatedAt (Datum aktualizace)
                    updated_at = pkg.get('UpdatedAt') or latest.get('UpdatedAt') or ""
                    if updated_at:
                        # Ořízneme čas, necháme jen datum (např. 2023-10-27)
                        updated_at = updated_at.split('T')[0]

                    results.append({
                        "name": name,
                        "id": pkg_id,
                        "version": version,
                        "icon_url": icon_url,
                        "website": "winget.run",
                        "tags": tags_str,
                        "updated": updated_at
                    })
            else:
                print(f"DEBUG API: Chyba serveru: {response.status_code}")

        except Exception as e:
            print(f"DEBUG API: Kritická chyba: {e}")
        
        return results

# --- IKONY ---
http_session = requests.Session()
http_session.headers.update({'User-Agent': 'Mozilla/5.0'})
icon_cache = {}

class IconLoader:
    @staticmethod
    def load_async(item_data, label_widget, root):
        app_id = item_data.get("id")
        website = item_data.get("website")
        direct_icon_url = item_data.get("icon_url")

        if app_id in icon_cache:
            IconLoader._update_label(label_widget, icon_cache[app_id])
            return
            
        thread = threading.Thread(target=IconLoader._download_strategy, args=(app_id, website, direct_icon_url, label_widget, root))
        thread.daemon = True
        thread.start()

    @staticmethod
    def _download_strategy(app_id, website, direct_url, label_widget, root):
        urls_to_try = []
        
        # 1. Priorita: URL přímo z API (pokud existuje)
        if direct_url:
            urls_to_try.append(direct_url)

        # 2. Priorita: GitHub repozitáře (protože API často ikony nevrací)
        if app_id and app_id != "Unknown":
            # WingetUI repozitář (velmi spolehlivý zdroj)
            urls_to_try.append(f"https://raw.githubusercontent.com/marticliment/WingetUI/main/src/wingetui/Assets/Packages/{app_id}.png")
            
            # Zkusíme zkrácené ID (např. jen 'Steam' z 'Valve.Steam')
            if "." in app_id:
                short_id = app_id.split(".")[-1]
                urls_to_try.append(f"https://raw.githubusercontent.com/marticliment/WingetUI/main/src/wingetui/Assets/Packages/{short_id}.png")
            
            # Dashboard Icons
            clean_id = app_id.lower().replace(".", "-")
            urls_to_try.append(f"https://cdn.jsdelivr.net/gh/walkxcode/dashboard-icons/png/{clean_id}.png")

        # 3. Priorita: Favicony z webu (jako poslední možnost)
        if website and website != "Unknown" and website != "winget.run":
            domain = IconLoader.get_clean_domain(website)
            if domain:
                urls_to_try.append(f"https://icons.duckduckgo.com/ip3/{domain}.ico")

        for url in urls_to_try:
            try:
                response = http_session.get(url, timeout=2.0)
                if response.status_code == 200 and len(response.content) > 100:
                    data = response.content
                    img = Image.open(BytesIO(data))
                    if img.mode != 'RGBA': img = img.convert('RGBA')
                    img = img.resize((32, 32), Image.Resampling.LANCZOS)
                    tk_img = ImageTk.PhotoImage(img)
                    if app_id: icon_cache[app_id] = tk_img
                    root.after(0, lambda: IconLoader._update_label(label_widget, tk_img))
                    return 
            except Exception: continue 

    @staticmethod
    def get_clean_domain(url):
        try:
            if not url or "://" not in url: url = "http://" + str(url)
            parsed = urlparse(url)
            domain = parsed.netloc
            if domain.startswith("www."): domain = domain[4:]
            return domain
        except: return None

    @staticmethod
    def _update_label(label, tk_img):
        try:
            label.config(image=tk_img)
            label.image = tk_img 
        except: pass

class ToolTip(object):
    def __init__(self, widget, text='widget info'):
        self.waittime = 400      
        self.wraplength = 180   
        self.widget = widget
        self.text = text
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)
        self.widget.bind("<ButtonPress>", self.leave)
        self.id = None
        self.tw = None

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hidetip()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(self.waittime, self.showtip)

    def unschedule(self):
        id = self.id
        self.id = None
        if id:
            self.widget.after_cancel(id)

    def showtip(self, event=None):
        x = y = 0
        x, y, cx, cy = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        self.tw = tk.Toplevel(self.widget)
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry("+%d+%d" % (x, y))
        label = tk.Label(self.tw, text=self.text, justify='left',
                       background="#2d2d2d", foreground="#ffffff",
                       relief='solid', borderwidth=1,
                       font=("Segoe UI", 8, "normal"), padx=5, pady=2)
        label.pack(ipadx=1)

    def hidetip(self):
        tw = self.tw
        self.tw= None
        if tw:
            tw.destroy()

class ModernScrollbar(tk.Canvas):
    def __init__(self, parent, command=None, width=10, bg=COLORS['bg_main'], thumb_color="#424242"):
        super().__init__(parent, width=width, bg=bg, highlightthickness=0)
        self.command = command
        self.thumb_color = thumb_color
        self.hover_color = "#4f4f4f"
        self.thumb = self.create_rectangle(0, 0, width, 0, fill=self.thumb_color, outline="")
        self.bind("<ButtonPress-1>", self.on_press)
        self.bind("<B1-Motion>", self.on_drag)
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)

    def set(self, first, last):
        self.top = float(first)
        self.bottom = float(last)
        self.redraw()

    def redraw(self):
        h = self.winfo_height()
        w = self.winfo_width()
        if h == 0: return
        if self.bottom - self.top >= 1.0:
            self.coords(self.thumb, 0, 0, 0, 0)
            return
        y1 = h * self.top
        y2 = h * self.bottom
        if y2 - y1 < 20: y2 = y1 + 20 
        self.coords(self.thumb, 2, y1, w-2, y2) 

    def on_press(self, event):
        self.y_start = event.y
        self.top_start = self.top

    def on_drag(self, event):
        h = self.winfo_height()
        delta = (event.y - self.y_start) / h
        new_top = self.top_start + delta
        if self.command: self.command("moveto", new_top)

    def on_enter(self, event): self.itemconfig(self.thumb, fill=self.hover_color)
    def on_leave(self, event): self.itemconfig(self.thumb, fill=self.thumb_color)