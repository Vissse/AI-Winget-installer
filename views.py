# views.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from google import genai 
from google.genai import types # Pro pokročilejší typy, pokud budou třeba
import json
import threading
import subprocess
import re
import webbrowser
from PIL import Image, ImageTk
from config import COLORS, OUTPUT_FILE
from utils import ToolTip, ModernScrollbar, IconLoader, SettingsManager
from install_manager import InstallationDialog
from updater import GitHubUpdater

class UpdaterPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=COLORS['bg_main'])
        self.controller = controller

        # --- Centered Container (Visual Match to Upcoming/Photo) ---
        # Používáme place() pro přesné vycentrování v rámci okna
        center_frame = tk.Frame(self, bg=COLORS['bg_main'])
        center_frame.place(relx=0.5, rely=0.5, anchor="center")

        # 1. Ikona
        # Používám textové emoji jako zástupný symbol (místo původního načítání obrázků).
        # Pokud chceš přesně tu ikonu z fotky, nahraď tento Label za Label s obrázkem (ImageTk).
        tk.Label(
            center_frame, 
            text="🔄",  # Zvoleno emoji pro Updater (nebo použij 📦)
            font=("Segoe UI Emoji", 48), 
            bg=COLORS['bg_main'], 
            fg=COLORS['sub_text'] # Šedá barva pro "neaktivní" vzhled
        ).pack(pady=(0, 20))

        # 2. Hlavní nadpis
        tk.Label(
            center_frame, 
            text="Vítejte v Updater", 
            font=("Segoe UI", 18, "bold"), 
            bg=COLORS['bg_main'], 
            fg="white"
        ).pack()

        # 3. Podnadpis / Instrukce
        tk.Label(
            center_frame, 
            text="Vyberte akci z menu vlevo",  # Text podle vzoru na fotce
            font=("Segoe UI", 10), 
            bg=COLORS['bg_main'], 
            fg=COLORS['sub_text']
        ).pack(pady=(5, 20))

        
# --- Installer Page ---
class InstallerPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=COLORS['bg_main'])
        self.controller = controller
        try: self.default_icon = ImageTk.PhotoImage(Image.new('RGB', (32, 32), color=COLORS['item_bg']))
        except: pass
        self.queue_data = {} 
        self.is_searching = False
        self.columnconfigure(0, weight=1, uniform="group1") 
        self.columnconfigure(1, weight=1, uniform="group1") 
        self.rowconfigure(0, weight=0) 
        self.rowconfigure(1, weight=0) 
        self.rowconfigure(2, weight=1) 
        header_frame = tk.Frame(self, bg=COLORS['bg_main'], pady=15)
        header_frame.grid(row=0, column=0, columnspan=2, sticky="ew")
        tk.Label(header_frame, text="Installer", font=("Segoe UI", 18, "bold"), bg=COLORS['bg_main'], fg=COLORS['fg']).pack(side="left", padx=20)
        left_controls = tk.Frame(self, bg=COLORS['bg_main'], padx=20)
        left_controls.grid(row=1, column=0, sticky="nsew")
        tk.Label(left_controls, text="Zadejte název programu", font=("Segoe UI", 14, "bold"), bg=COLORS['bg_main'], fg=COLORS['fg'], anchor="w").pack(fill='x')
        tk.Label(left_controls, text="(Nebo popište, co hledáte, např. 'úprava zvuku')", font=("Segoe UI", 9), bg=COLORS['bg_main'], fg=COLORS['sub_text'], anchor="w").pack(fill='x', pady=(0, 10))
        search_frame = tk.Frame(left_controls, bg=COLORS['bg_main'])
        search_frame.pack(fill='x', pady=(0, 10))
        search_border = tk.Frame(search_frame, bg=COLORS['input_bg'], bd=0, highlightthickness=0) 
        search_border.pack(fill='x', ipady=2)
        self.input_entry = tk.Entry(search_border, font=("Segoe UI", 12), bg=COLORS['input_bg'], fg="white", insertbackground="white", relief="flat")
        self.input_entry.pack(side='left', fill='both', expand=True, padx=10)
        self.input_entry.bind('<Return>', lambda event: self.start_search())
        self.search_btn = self.create_animated_btn(search_border, "Hledat", self.start_search, COLORS['accent'], COLORS['accent_hover'])
        self.search_btn.pack(side='right', fill='y', padx=2, pady=2)
        style = ttk.Style()
        style.theme_use('default')
        style.configure("Horizontal.TProgressbar", background=COLORS['accent'], troughcolor=COLORS['bg_main'], borderwidth=0, thickness=2)
        self.progress = ttk.Progressbar(search_frame, orient="horizontal", mode="indeterminate", style="Horizontal.TProgressbar")
        tk.Label(left_controls, text="Výsledky hledání:", font=("Segoe UI", 11, "bold"), bg=COLORS['bg_main'], fg=COLORS['sub_text'], anchor="w").pack(fill='x', pady=(10, 5), side="bottom")
        right_controls = tk.Frame(self, bg=COLORS['bg_main'], padx=20)
        right_controls.grid(row=1, column=1, sticky="sew") 
        queue_header_row = tk.Frame(right_controls, bg=COLORS['bg_main'])
        queue_header_row.pack(fill='x', pady=(10, 5), side="bottom")
        tk.Label(queue_header_row, text="Instalační fronta:", font=("Segoe UI", 11, "bold"), bg=COLORS['bg_main'], fg=COLORS['sub_text']).pack(side="left")
        actions_frame = tk.Frame(queue_header_row, bg=COLORS['bg_main'])
        actions_frame.pack(side="right")
        self.create_header_btn(actions_frame, "📂", self.import_queue, "Importovat seznam", COLORS['input_bg'], COLORS['item_hover'])
        self.create_header_btn(actions_frame, "🗑️", self.clear_queue, "Vymazat frontu", COLORS['danger'], COLORS['danger_hover'])
        self.create_header_btn(actions_frame, "💾", self.save_only, "Uložit .bat soubor", COLORS['input_bg'], COLORS['item_hover'])
        self.create_header_btn(actions_frame, "🚀", self.install_now, "Instalovat vše", COLORS['success'], COLORS['success_hover'])
        left_list_frame = tk.Frame(self, bg=COLORS['bg_main'], padx=20)
        left_list_frame.grid(row=2, column=0, sticky="nsew")
        self.found_container = tk.Frame(left_list_frame, bg=COLORS['bg_sidebar'])
        self.found_container.pack(fill='both', expand=True, pady=(0, 20))
        self.found_canvas = tk.Canvas(self.found_container, bg=COLORS['bg_sidebar'], highlightthickness=0)
        self.found_scrollbar = ModernScrollbar(self.found_container, command=self.found_canvas.yview, bg=COLORS['bg_sidebar'])
        self.found_scrollable = tk.Frame(self.found_canvas, bg=COLORS['bg_sidebar'])
        self.found_scrollable.bind("<Configure>", self.on_frame_configure)
        self.found_canvas.create_window((0, 0), window=self.found_scrollable, anchor="nw", width=480)
        self.found_canvas.configure(yscrollcommand=self.found_scrollbar.set)
        self.found_canvas.bind("<Configure>", lambda e: self.found_canvas.itemconfig(self.found_canvas.find_all()[0], width=e.width))
        self.found_canvas.pack(side="left", fill="both", expand=True)
        self.found_scrollbar.pack(side="right", fill="y")
        self._bind_mousewheel(self.found_container, self.found_canvas)
        right_list_frame = tk.Frame(self, bg=COLORS['bg_main'], padx=20)
        right_list_frame.grid(row=2, column=1, sticky="nsew")
        self.queue_container = tk.Frame(right_list_frame, bg=COLORS['bg_sidebar'])
        self.queue_container.pack(fill='both', expand=True, pady=(0, 20))
        self.queue_canvas = tk.Canvas(self.queue_container, bg=COLORS['bg_sidebar'], highlightthickness=0)
        self.queue_scrollbar = ModernScrollbar(self.queue_container, command=self.queue_canvas.yview, bg=COLORS['bg_sidebar'])
        self.queue_scrollable = tk.Frame(self.queue_canvas, bg=COLORS['bg_sidebar'])
        self.queue_scrollable.bind("<Configure>", lambda e: self.queue_canvas.configure(scrollregion=self.queue_canvas.bbox("all")))
        self.queue_canvas.create_window((0, 0), window=self.queue_scrollable, anchor="nw", width=480)
        self.queue_canvas.configure(yscrollcommand=self.queue_scrollbar.set)
        self.queue_canvas.bind("<Configure>", lambda e: self.queue_canvas.itemconfig(self.queue_canvas.find_all()[0], width=e.width))
        self.queue_canvas.pack(side="left", fill="both", expand=True)
        self.queue_scrollbar.pack(side="right", fill="y")
        self._bind_mousewheel(self.queue_container, self.queue_canvas)

    def on_frame_configure(self, event):
        self.found_canvas.configure(scrollregion=self.found_canvas.bbox("all"))

    def create_animated_btn(self, parent, text, command, bg_color, hover_color):
        btn = tk.Button(parent, text=text, command=command, bg=bg_color, fg="white", font=("Segoe UI", 10, "bold"), relief="flat", padx=15, pady=8, cursor="hand2", borderwidth=0)
        def on_enter(e):
            if btn['state'] != 'disabled': btn.config(bg=hover_color)
        def on_leave(e):
            if btn['state'] != 'disabled': btn.config(bg=bg_color)
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        return btn

    def create_header_btn(self, parent, text, command, tooltip_text, bg_color, hover_color):
        btn = tk.Button(parent, text=text, command=command, bg=bg_color, fg="white", font=("Segoe UI Emoji", 12), relief="flat", width=3, cursor="hand2", borderwidth=0)
        btn.pack(side="left", padx=2)
        def on_enter(e):
            if btn['state'] != 'disabled': btn.config(bg=hover_color)
        def on_leave(e):
            if btn['state'] != 'disabled': btn.config(bg=bg_color)
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        ToolTip(btn, tooltip_text)
        return btn

    def import_queue(self):
        file_path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt"), ("Batch files", "*.bat"), ("All files", "*.*")])
        if file_path:
             messagebox.showinfo("Import", f"Vybrán soubor: {file_path}\n(Funkce importu zatím není plně implementována)")

    def _bind_mousewheel(self, widget, canvas):
        def _on_mousewheel(event):
            if canvas.bbox("all"):
                scroll_height = canvas.bbox("all")[3]
                visible_height = canvas.winfo_height()
                if scroll_height <= visible_height: return 
            if event.num == 5 or event.delta < 0: canvas.yview_scroll(1, "units")
            elif event.num == 4 or event.delta > 0: canvas.yview_scroll(-1, "units")
            self.found_scrollbar.redraw()
            self.queue_scrollbar.redraw()
        bind_enter = lambda e: {canvas.bind_all("<MouseWheel>", _on_mousewheel), canvas.bind_all("<Button-4>", _on_mousewheel), canvas.bind_all("<Button-5>", _on_mousewheel)}
        bind_leave = lambda e: {canvas.unbind_all("<MouseWheel>"), canvas.unbind_all("<Button-4>"), canvas.unbind_all("<Button-5>")}
        widget.bind('<Enter>', bind_enter)
        widget.bind('<Leave>', bind_leave)

    def start_search(self):
        user_request = self.input_entry.get()
        if not user_request:
            messagebox.showwarning("Chyba", "Napiš název programu.")
            return
        if self.is_searching: return 
        self.is_searching = True
        self.search_btn.config(cursor="arrow") 
        self.input_entry.delete(0, 'end') 
        self.progress.pack(fill='x', pady=(5, 0))
        self.progress.start(10) 
        threading.Thread(target=self.get_winget_ids_thread, args=(user_request,)).start()

# Předpokládám, že WingetRunAPI a self.controller/self.progress jsou definovány jinde

    def get_winget_ids_thread(self, user_request):
        # 1. Načtení klíče
        settings = SettingsManager.load_settings()
        api_key = settings.get("api_key", "")
        
        print(f"--- FÁZE 1: Zjišťování záměru pro: '{user_request}' ---")
        
        # 2. Inicializace klienta (NOVÉ SDK)
        try:
            client = genai.Client(api_key=api_key)
        except Exception as e:
            print(f"Chyba init AI: {e}")
            self.controller.after(0, self.stop_loading_animation)
            return

        intent_prompt = f"""
        Jsi expert na Windows software a Winget repozitář.
        Uživatel zadal: "{user_request}"
        Pokud hledá konkrétní app, vrať jen opravený název.
        Pokud hledá kategorii, vrať seznam nejlepších aplikací.
        Odpověz POUZE ve formátu: QUERIES: app1;app2;app3
        """

        search_terms = []
        try:
            # NOVÉ VOLÁNÍ API
            response = client.models.generate_content(
                model="gemini-2.5-flash", 
                contents=intent_prompt
            )
            raw_intent = response.text.strip()
            
            if "QUERIES:" in raw_intent:
                clean_line = raw_intent.replace("QUERIES:", "").strip()
                search_terms = [t.strip() for t in clean_line.split(";") if t.strip()]
            else:
                search_terms = [user_request]
            print(f"AI navrhlo: {search_terms}")

        except Exception as e:
            print(f"Chyba AI intent: {e}")
            search_terms = [user_request]

        # 2. KROK: Hromadné hledání ve Winget
        # Spustíme hledání pro každý výraz, který AI navrhlo
        combined_output = ""
        
        self.progress['maximum'] = len(search_terms) * 100
        current_prog = 0
        
        for term in search_terms:
            try:
                cmd = f'winget search "{term}" --source winget --accept-source-agreements -n 3'
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                result = subprocess.run(cmd, capture_output=True, text=True, startupinfo=startupinfo, encoding='cp852', errors='replace')
                combined_output += f"\n--- VÝSLEDKY PRO '{term}' ---\n" + result.stdout
            except: pass
            
            # Aktualizace progress baru (jen vizuálně)
            current_prog += 100
            # V threadu nemůžeme přímo měnit GUI bezpečně, ale u jednoduchých proměnných to v Tkinteru často projde. 
            # Správnější by bylo frontování, ale pro jednoduchost necháme běžet.

        # 3. KROK: Finální filtrace a formátování na JSON
        # Teď máme "špinavý" výstup z několika hledání, AI z toho musí vytáhnout to důležité.
        
        filter_prompt = f"""
        Mám výstup z příkazové řádky (Winget Search) pro různé hledané výrazy.
        Původní dotaz uživatele byl: "{user_request}"
        
        SUROVÁ DATA Z WINGET:
        '''
        {combined_output}
        '''

        INSTRUKCE:
        1. Analyzuj surová data a najdi aplikace, které odpovídají záměru uživatele.
        2. Pokud data obsahují balast (knihovny, ovladače), ignoruj je. Hledáme hlavní aplikace. (bez duplicit - žádné Bety ani jiné alternativní verze určitého programu). Pokud se budou nacházet dvě verze určitého programu např. GIMP má z nějakého důvodu ve wingetu 2 verze, vždy vyber tu novější.
        3. Extrahuj Název, ID a Verzi.
        4. Pokud ID nevidíš v datech, ale jsi si jistý, že to je ta správná aplikace (např. jsi ji sám navrhl v předchozím kroku), pokus se ID odhadnout (např. 'Mozilla.Firefox').
        
        VÝSTUPNÍ FORMÁT (čistý JSON pole):
        [
            {{ 
                "name": "Název aplikace", 
                "id": "Přesné.ID", 
                "version": "verze (nebo 'Latest')", 
                "website": "domena.com" 
            }}
        ]
        """

        try:
            # NOVÉ VOLÁNÍ API
            response = client.models.generate_content(
                model="gemini-2.5-flash", 
                contents=filter_prompt
            )
            raw_text = response.text
            json_str = raw_text.replace("```json", "").replace("```", "").strip()
            match = re.search(r'\[.*\]', json_str, re.DOTALL)
            data = json.loads(match.group(0)) if match else []

            for item in data:
                if not item.get('version') or item['version'] == "Latest": item['version'] = "Latest/Unknown"

            self.controller.after(0, self.display_search_results, data)

        except Exception as e:
            print(f"Chyba parsování: {e}")
            self.controller.after(0, self.stop_loading_animation)

    def stop_loading_animation(self):
        self.progress.stop()
        self.progress.pack_forget()
        self.is_searching = False
        self.search_btn.config(cursor="hand2")

    def display_search_results(self, items):
        self.stop_loading_animation()
        for widget in self.found_scrollable.winfo_children(): widget.destroy()
        if not items:
            tk.Label(self.found_scrollable, text="Nic nenalezeno.", bg=COLORS['bg_sidebar'], fg="gray").pack(pady=20)
            return
        for item in items: self.create_list_item(self.found_scrollable, item, is_result_mode=True)
        self.found_canvas.update_idletasks()
        self.found_scrollbar.redraw()

    def create_list_item(self, parent_scrollable, item_data, is_result_mode):
        name = item_data.get("name")
        app_id = item_data.get("id")
        version = item_data.get("version")
        card = tk.Frame(parent_scrollable, bg=COLORS['item_bg'], pady=10, padx=10)
        card.pack(fill='x', padx=(10,0), pady=5)
        icon_label = tk.Label(card, image=self.default_icon, bg=COLORS['item_bg'])
        icon_label.pack(side="left", padx=(0, 15))
        
        # Načítání ikon (nyní podporuje i icon_url z API)
        IconLoader.load_async(item_data, icon_label, self.controller)
        
        text_frame = tk.Frame(card, bg=COLORS['item_bg'])
        text_frame.pack(side="left", fill="both", expand=True)
        tk.Label(text_frame, text=name, font=("Segoe UI", 11, "bold"), bg=COLORS['item_bg'], fg="white", anchor="w").pack(fill="x")
        tk.Label(text_frame, text=f"ID: {app_id} | v{version}", font=("Segoe UI", 9), bg=COLORS['item_bg'], fg=COLORS['sub_text'], anchor="w").pack(fill="x")
        action_symbol = tk.Label(card, font=("Arial", 18), bg=COLORS['item_bg'], cursor="hand2", padx=10)
        action_symbol.pack(side="right")
        if is_result_mode:
            action_symbol.config(text="＋", fg=COLORS['accent'])
            action_symbol.bind("<Button-1>", lambda e, i=item_data: self.add_item_to_queue(i))
            self._bind_symbol_hover(action_symbol, COLORS['accent'], COLORS['fg'])
        else:
            action_symbol.config(text="✕", fg=COLORS['danger'])
            action_symbol.bind("<Button-1>", lambda e, aid=app_id: self.remove_from_queue(aid))
            self._bind_symbol_hover(action_symbol, COLORS['danger'], COLORS['fg'])
        self._bind_card_hover(card, text_frame, icon_label, action_symbol)

    def _bind_symbol_hover(self, widget, hover_bg, hover_fg):
        normal_bg = COLORS['item_bg']
        normal_fg = widget.cget("fg")
        def on_enter(e): widget.config(bg=hover_bg, fg=hover_fg)
        def on_leave(e): widget.config(bg=normal_bg, fg=normal_fg)
        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)

    def _bind_card_hover(self, card, text_frame, icon_label, action_symbol):
        widgets_to_change = [card, text_frame, icon_label] + text_frame.winfo_children()
        def on_enter(e):
            for w in widgets_to_change: w.config(bg=COLORS['item_hover'])
            if e.widget != action_symbol: action_symbol.config(bg=COLORS['item_hover'])
        def on_leave(e):
            for w in widgets_to_change: w.config(bg=COLORS['item_bg'])
            if e.widget != action_symbol: action_symbol.config(bg=COLORS['item_bg'])
        card.bind("<Enter>", on_enter)
        card.bind("<Leave>", on_leave)

    def add_item_to_queue(self, item_data):
        app_id = item_data.get("id")
        if app_id in self.queue_data: return
        self.queue_data[app_id] = item_data
        self.create_list_item(self.queue_scrollable, item_data, is_result_mode=False)
        self.queue_canvas.update_idletasks()
        self.queue_canvas.yview_moveto(1.0)
        self.queue_scrollbar.redraw()

    def remove_from_queue(self, app_id):
        if app_id in self.queue_data:
            del self.queue_data[app_id]
            self.refresh_queue_view()

    def refresh_queue_view(self):
        for widget in self.queue_scrollable.winfo_children(): widget.destroy()
        for app_id, item_data in self.queue_data.items():
            self.create_list_item(self.queue_scrollable, item_data, is_result_mode=False)
        self.queue_canvas.update_idletasks()
        self.queue_scrollbar.redraw()

    def clear_queue(self):
        self.queue_data = {}
        self.refresh_queue_view()

    def _create_batch_file(self):
        if not self.queue_data:
            messagebox.showwarning("Pozor", "Seznam je prázdný.")
            return False
        try:
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f: 
                f.write("@echo off\nchcp 65001 > nul\necho Zahajuji instalaci...\n\n")
                for aid, data in self.queue_data.items():
                    f.write(f"echo Instaluji: {data['name']}...\n")
                    f.write(f"winget install -e --id {aid} --silent --accept-package-agreements --accept-source-agreements\n")
                    f.write("echo ----------------------------------------\n")
                f.write("\necho Hotovo!\n")
            return True
        except Exception as e:
            messagebox.showerror("Chyba", str(e))
            return False

    def save_only(self):
        if self._create_batch_file(): 
            messagebox.showinfo("Uloženo", f"Soubor: {OUTPUT_FILE}")

    def install_now(self):
        if not self.queue_data:
            messagebox.showwarning("Pozor", "Seznam je prázdný.")
            return
        InstallationDialog(self.controller, list(self.queue_data.values()))

class PlaceholderPage(tk.Frame):
    def __init__(self, parent, title, icon_emoji="✨"):
        super().__init__(parent, bg=COLORS['bg_main'])
        center_frame = tk.Frame(self, bg=COLORS['bg_main'])
        center_frame.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(center_frame, text=icon_emoji, font=("Segoe UI Emoji", 48), bg=COLORS['bg_main']).pack(pady=(0, 20))
        tk.Label(center_frame, text=f"Vítejte v {title}", font=("Segoe UI", 18, "bold"), bg=COLORS['bg_main'], fg="white").pack()
        tk.Label(center_frame, text="Vyberte akci z menu vlevo", font=("Segoe UI", 10), bg=COLORS['bg_main'], fg=COLORS['sub_text']).pack(pady=(5, 20))


class HealthCheckPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=COLORS['bg_main'])
        self.controller = controller
        
        # 1. Hlavní nadpis
        header = tk.Frame(self, bg=COLORS['bg_main'], pady=20, padx=20)
        header.pack(fill='x')
        tk.Label(header, text="Windows Health & Maintenance", font=("Segoe UI", 18, "bold"), bg=COLORS['bg_main'], fg="white").pack(side="left")

        # 2. Kontejner pro obsah
        content = tk.Frame(self, bg=COLORS['bg_main'], padx=20)
        content.pack(fill='both', expand=True)

        # --- LEVÝ PANEL (Ovládání) ---
        controls = tk.Frame(content, bg=COLORS['bg_sidebar'], padx=15, pady=15)
        controls.pack(side="left", fill="y", padx=(0, 20))
        
        # Sekce Opravy Systému (Zůstává, to je základ zdraví PC)
        tk.Label(controls, text="Opravy Systému", font=("Segoe UI", 11, "bold"), bg=COLORS['bg_sidebar'], fg=COLORS['accent']).pack(anchor="w", pady=(0, 10))

        self.create_tool_row(controls, "🔍", "SFC Scan", 
                             "sfc /scannow", 
                             "Kontrola integrity souborů (SFC)...",
                             "System File Checker (SFC).\nSkenuje integritu všech chráněných systémových souborů\na nahrazuje poškozené verze kopií z mezipaměti.\nZákladní první krok při opravě systému.")

        self.create_tool_row(controls, "💾", "CHKDSK Scan (Disk)", 
                             "chkdsk C: /scan", 
                             "Online kontrola disku (CHKDSK)...",
                             "Check Disk (Scan Mode).\nZkontroluje logickou strukturu souborového systému (NTFS)\na hledá chyby na disku C:.\nBěží za chodu Windows bez nutnosti restartu.")

        self.create_tool_row(controls, "🩺", "DISM Check Health", 
                             "dism /online /cleanup-image /CheckHealth", 
                             "Rychlá kontrola obrazu (DISM)...",
                             "DISM (CheckHealth).\nPouze zkontroluje, zda byl obraz systému označen jako poškozený.\nNeprovádí žádné opravy, slouží jen k rychlé diagnostice.")

        self.create_tool_row(controls, "🛠️", "DISM Restore Health", 
                             "dism /online /cleanup-image /RestoreHealth", 
                             "Hloubková oprava obrazu (DISM)...",
                             "DISM (RestoreHealth).\nPokročilá oprava obrazu Windows.\nStáhne funkční soubory z Windows Update a opraví poškozené\nkomponenty, které SFC nedokázal vyřešit.")
        
        # Sekce Správa PC (NOVÉ - Místo sítě a wingetu)
        tk.Label(controls, text="Správa PC a Údržba", font=("Segoe UI", 11, "bold"), bg=COLORS['bg_sidebar'], fg=COLORS['accent']).pack(anchor="w", pady=(20, 10))
        
        self.create_tool_row(controls, "🗑️", "Smazat Temp soubory", 
                             'del /q/f/s %TEMP%\\*', 
                             "Mazání dočasných souborů uživatele...",
                             "Temp Cleaner.\nBezpečně vymaže obsah složky %TEMP%.\nOdstraní zbytečné soubory po instalacích a cache aplikací.\n(Soubory, které systém právě používá, budou přeskočeny).")

        self.create_tool_row(controls, "💿", "Vyčištění Disku (Windows)", 
                             "cleanmgr.exe", 
                             "Spouštění nástroje Vyčištění disku...",
                             "Windows Disk Cleanup.\nSpustí oficiální nástroj Windows pro uvolnění místa.\nUmožní smazat Koš, miniatury, logy a staré aktualizace.")

        self.create_tool_row(controls, "🔋", "Report Baterie (Laptop)", 
                             "powercfg /batteryreport /output \"C:\\battery_report.html\"", 
                             "Generování reportu baterie...",
                             "PowerCfg Battery Report.\nVygeneruje detailní HTML report o zdraví baterie notebooku.\nSoubor bude uložen přímo na disk C:\\battery_report.html\n(Obsahuje historii nabíjení a reálnou kapacitu).")
        
        self.create_tool_row(controls, "🧹", "WinSxS Cleanup (Deep)", 
                             "dism /online /cleanup-image /StartComponentCleanup", 
                             "Hloubkové čištění systémových záloh...",
                             "Component Cleanup.\nAnalyzuje složku WinSxS a odstraňuje staré verze\naktualizací Windows, které již nejsou potřeba.\nUvolní místo na disku, ale znemožní odinstalaci aktualizací.")

        # --- PRAVÝ PANEL (Log výstup) ---
        log_frame = tk.Frame(content, bg=COLORS['bg_main'])
        log_frame.pack(side="right", fill="both", expand=True)

        tk.Label(log_frame, text="Průběh operace:", font=("Segoe UI", 10), bg=COLORS['bg_main'], fg=COLORS['sub_text']).pack(anchor="w", pady=(0, 5))

        self.console = tk.Text(log_frame, bg="#0d0d0d", fg="#cccccc", font=("Consolas", 10), relief="flat", padx=10, pady=10, state="disabled")
        self.console.pack(fill="both", expand=True)

        try:
            scrollbar = ModernScrollbar(log_frame, command=self.console.yview, bg=COLORS['bg_main'])
            scrollbar.pack(side="right", fill="y", before=self.console)
            self.console.config(yscrollcommand=scrollbar.set)
        except: pass

    def create_tool_row(self, parent, icon, title, command, log_desc, tooltip_text):
        """Vytvoří řádek s perfektně zarovnaným 'tlačítkem' a ikonou lupy."""
        row = tk.Frame(parent, bg=COLORS['bg_sidebar'])
        row.pack(fill='x', pady=2)

        # --- 1. KOMPLEXNÍ TLAČÍTKO ---
        btn_frame = tk.Frame(row, bg=COLORS['input_bg'], cursor="hand2", height=35)
        btn_frame.pack(side="left", fill="y")
        btn_frame.pack_propagate(False) 
        btn_frame.configure(width=280)  

        # Ikona 
        lbl_icon = tk.Label(btn_frame, text=icon, font=("Segoe UI Emoji", 11), 
                            bg=COLORS['input_bg'], fg="white", width=4, cursor="hand2")
        lbl_icon.pack(side="left", fill="y")

        # Text
        lbl_text = tk.Label(btn_frame, text=title, font=("Segoe UI", 10), 
                            bg=COLORS['input_bg'], fg="white", anchor="w", cursor="hand2")
        lbl_text.pack(side="left", fill="both", expand=True)

        # Logika kliknutí
        def on_click(e): self.run_command(command, log_desc)
        
        btn_frame.bind("<Button-1>", on_click)
        lbl_icon.bind("<Button-1>", on_click)
        lbl_text.bind("<Button-1>", on_click)

        # Hover efekt
        widgets_to_color = [btn_frame, lbl_icon, lbl_text]
        
        def on_btn_enter(e): 
            for w in widgets_to_color: w.config(bg=COLORS['item_hover'])
        def on_btn_leave(e): 
            for w in widgets_to_color: w.config(bg=COLORS['input_bg'])

        for w in widgets_to_color:
            w.bind("<Enter>", on_btn_enter)
            w.bind("<Leave>", on_btn_leave)


        # --- 2. Info ikona (Lupa) ---
        base_font = ("Segoe UI Emoji", 12)

        info_lbl = tk.Label(row, text="🔍", font=base_font, 
                            bg=COLORS['bg_sidebar'], fg=COLORS['sub_text'], cursor="hand2")
        info_lbl.pack(side="left", padx=(8, 0)) 
        
        # Tooltip logika
        info_lbl.tooltip_win = None
        info_lbl.timer_id = None

        def show_tooltip():
            if info_lbl.tooltip_win: return
            x, y, cx, cy = info_lbl.bbox("insert")
            x += info_lbl.winfo_rootx() + 30
            y += info_lbl.winfo_rooty() + 10
            
            tw = tk.Toplevel(info_lbl)
            tw.wm_overrideredirect(True)
            tw.wm_geometry(f"+{x}+{y}")
            
            label = tk.Label(tw, text=tooltip_text, justify='left',
                           background="#2d2d2d", foreground="#ffffff",
                           relief='solid', borderwidth=1,
                           font=("Segoe UI", 9), padx=8, pady=5)
            label.pack()
            info_lbl.tooltip_win = tw

        def on_info_enter(e):
            info_lbl.config(fg=COLORS['accent'])
            info_lbl.timer_id = info_lbl.after(400, show_tooltip)

        def on_info_leave(e):
            info_lbl.config(fg=COLORS['sub_text'])
            if info_lbl.timer_id:
                info_lbl.after_cancel(info_lbl.timer_id)
                info_lbl.timer_id = None
            if info_lbl.tooltip_win:
                info_lbl.tooltip_win.destroy()
                info_lbl.tooltip_win = None
            
        info_lbl.bind("<Enter>", on_info_enter)
        info_lbl.bind("<Leave>", on_info_leave)

        return row

    def log(self, text):
        self.console.config(state="normal")
        self.console.insert(tk.END, text + "\n")
        self.console.see(tk.END)
        self.console.config(state="disabled")

    def run_command(self, cmd, description):
        self.console.config(state="normal")
        self.console.delete(1.0, tk.END)
        self.console.config(state="disabled")
        
        self.log(f"--- ZAHAJUJI: {description} ---")
        self.log(f"Příkaz: {cmd}")
        self.log("(Operace běží na pozadí, prosím čekejte...)\n")
        
        import threading
        import subprocess
        threading.Thread(target=self._execute_thread, args=(cmd,), daemon=True).start()

    def _execute_thread(self, cmd):
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            # Použijeme cmd.exe /c pro složitější příkazy (jako del)
            if cmd.startswith("del"):
                 full_cmd = f"cmd /c {cmd}"
            else:
                 full_cmd = f"chcp 65001 > nul && {cmd}"

            process = subprocess.Popen(full_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                       shell=True, text=True, encoding="utf-8", errors="replace", 
                                       startupinfo=startupinfo)
            
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                if line:
                    self.controller.after(0, lambda l=line.strip(): self.log(l))
            
            rc = process.poll()
            if rc == 0:
                self.controller.after(0, lambda: self.log("\n✅ HOTOVO: Operace dokončena úspěšně."))
            else:
                self.controller.after(0, lambda: self.log(f"\n❌ CHYBA (Kód {rc}).\nUjistěte se, že je aplikace spuštěna jako SPRÁVCE."))
                
        except Exception as e:
            self.controller.after(0, lambda: self.log(f"Kritická chyba: {e}"))

class SettingsPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=COLORS['bg_main'])
        self.controller = controller
        
        # Načtení aktuálního klíče
        self.settings = SettingsManager.load_settings()
        current_key = self.settings.get("api_key", "")

        # 1. Hlavní nadpis
        header = tk.Frame(self, bg=COLORS['bg_main'], pady=20, padx=20)
        header.pack(fill='x')
        tk.Label(header, text="Uživatelské nastavení", font=("Segoe UI", 18, "bold"), bg=COLORS['bg_main'], fg="white").pack(side="left")

        # 2. Kontejner
        content = tk.Frame(self, bg=COLORS['bg_main'], padx=20)
        content.pack(fill='both', expand=True)

        # --- SEKCE API ---
        api_frame = tk.Frame(content, bg=COLORS['bg_sidebar'], padx=20, pady=20)
        api_frame.pack(fill='x', pady=(0, 20))

        tk.Label(api_frame, text="Gemini API Klíč", font=("Segoe UI", 12, "bold"), bg=COLORS['bg_sidebar'], fg="white").pack(anchor="w")
        tk.Label(api_frame, text="Pro fungování AI vyhledávání je potřeba Google Gemini API klíč.", font=("Segoe UI", 9), bg=COLORS['bg_sidebar'], fg=COLORS['sub_text']).pack(anchor="w", pady=(0, 10))

        # Vstupní pole
        entry_bg = tk.Frame(api_frame, bg=COLORS['input_bg'], padx=10, pady=5)
        entry_bg.pack(fill='x')
        
        self.api_entry = tk.Entry(entry_bg, font=("Consolas", 11), bg=COLORS['input_bg'], fg="white", insertbackground="white", relief="flat")
        self.api_entry.pack(fill='x')
        self.api_entry.insert(0, current_key)

        # Odkaz na získání klíče
        link_lbl = tk.Label(api_frame, text="🔗 Získat API klíč zdarma (Google AI Studio)", font=("Segoe UI", 9, "underline"), bg=COLORS['bg_sidebar'], fg=COLORS['accent'], cursor="hand2")
        link_lbl.pack(anchor="w", pady=(10, 5))
        link_lbl.bind("<Button-1>", lambda e: webbrowser.open("https://aistudio.google.com/app/apikey"))

        
        # Tlačítka
        btn_frame = tk.Frame(api_frame, bg=COLORS['bg_sidebar'])
        btn_frame.pack(fill='x', pady=(20, 0))

        # ZMĚNA: Barva 'bg' změněna na COLORS['accent']
        save_btn = tk.Button(btn_frame, text="💾 Uložit klíč", command=self.save_key,
                             bg=COLORS['accent'], fg="white", font=("Segoe UI", 10, "bold"),
                             relief="flat", padx=20, pady=8, cursor="hand2")
        save_btn.pack(side="left")

        # Přidání hover efektu pro modré tlačítko
        def on_save_enter(e): save_btn.config(bg=COLORS['accent_hover'])
        def on_save_leave(e): save_btn.config(bg=COLORS['accent'])
        save_btn.bind("<Enter>", on_save_enter)
        save_btn.bind("<Leave>", on_save_leave)

        check_btn = tk.Button(btn_frame, text="⚡ Ověřit stav limitu", command=self.check_api_status,
                             bg=COLORS['input_bg'], fg="white", font=("Segoe UI", 10),
                             relief="flat", padx=20, pady=8, cursor="hand2")
        check_btn.pack(side="left", padx=10)

        # --- STATUS PANEL ---
        self.status_frame = tk.Frame(content, bg=COLORS['bg_main'], pady=20)
        self.status_frame.pack(fill='x')
        self.status_label = tk.Label(self.status_frame, text="", font=("Segoe UI", 10), bg=COLORS['bg_main'])
        self.status_label.pack(anchor="w")

        update_btn = tk.Button(btn_frame, text="🔄 Zkontrolovat update", 
                             command=self.check_update,
                             bg=COLORS['input_bg'], fg="white", font=("Segoe UI", 10),
                             relief="flat", padx=20, pady=8, cursor="hand2")
        update_btn.pack(side="left", padx=10)
  
        quota_btn = tk.Button(btn_frame, text="📊 Graf spotřeby", 
                             command=lambda: webbrowser.open("https://aistudio.google.com/app/usage?timeRange=last-90-days"),
                             bg=COLORS['input_bg'], fg="white", font=("Segoe UI", 10),
                             relief="flat", padx=20, pady=8, cursor="hand2")
        quota_btn.pack(side="left", padx=10)

        # Přidáme hover efekt (aby tlačítko reagovalo na myš)
        def on_quota_enter(e): quota_btn.config(bg=COLORS['item_hover'])
        def on_quota_leave(e): quota_btn.config(bg=COLORS['input_bg'])
        quota_btn.bind("<Enter>", on_quota_enter)
        quota_btn.bind("<Leave>", on_quota_leave)

    def save_key(self):
        new_key = self.api_entry.get().strip()
        self.settings["api_key"] = new_key
        
        if SettingsManager.save_settings(self.settings):
            # V novém SDK už není potřeba volat genai.configure()!
            # Klíč se použije automaticky při dalším volání AI.
            messagebox.showinfo("Úspěch", "API klíč byl uložen.")
        else:
            messagebox.showerror("Chyba", "Nepodařilo se uložit nastavení.")

    def check_api_status(self):
        key = self.api_entry.get().strip()
        if not key:
            self.update_status("⚠️ Chybí API klíč.", "orange")
            return

        self.update_status("⏳ Ověřuji spojení s Google AI...", COLORS['sub_text'])
        
        # Spustíme test ve vlákně, aby nezamrzlo GUI
        threading.Thread(target=self._test_connection_thread, args=(key,), daemon=True).start()

    def _test_connection_thread(self, key):
        try:
            # NOVÉ SDK: Inicializace klienta
            client = genai.Client(api_key=key)
            
            # NOVÉ SDK: Generování obsahu (Test)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents="Hello",
                config=types.GenerateContentConfig(max_output_tokens=5)
            )
            
            if response and response.text:
                self.controller.after(0, lambda: self.update_status("✅ Klíč je AKTIVNÍ (GenAI SDK).", COLORS['success']))
            else:
                self.controller.after(0, lambda: self.update_status("❌ Žádná odpověď.", COLORS['danger']))
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg:
                msg = "⚠️ Limit vyčerpán (429)."
                color = "orange"
            elif "400" in error_msg or "INVALID_ARGUMENT" in error_msg:
                msg = "❌ Neplatný API klíč."
                color = COLORS['danger']
            else:
                msg = f"❌ Chyba: {error_msg[:30]}..."
                color = COLORS['danger']
            
            self.controller.after(0, lambda: self.update_status(msg, color))

    def update_status(self, text, color):
        self.status_label.config(text=text, fg=color)

    def check_update(self):
        updater = GitHubUpdater(self)
        threading.Thread(target=lambda: updater.check_for_updates(silent=False))