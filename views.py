# views.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import google.generativeai as genai
import json
import threading
import subprocess
import re
from PIL import Image, ImageTk
from config import COLORS, OUTPUT_FILE
from utils import ToolTip, ModernScrollbar, IconLoader, WingetRunAPI  # <--- PŘIDÁN IMPORT API
from install_manager import InstallationDialog

# --- Updater Page ---
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import subprocess
import re
from PIL import Image, ImageTk

# Předpokládám, že ModernScrollbar, COLORS, IconLoader a další máte importované
# Pokud ne, nechte tam své původní importy

class UpdaterPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=COLORS['bg_main'])
        self.controller = controller
        
        # Cache pro ikonky
        self.icon_cache = {} 
        self.rendering_task = None  # Pro uložení ID úlohy vykreslování
        self.stop_rendering = False # Vlajka pro zastavení vykreslování
        
        try:
            self.default_icon = ImageTk.PhotoImage(Image.new('RGB', (32, 32), color=COLORS['item_bg']))
        except: pass

        self.upgradable_apps = [] 

        # --- GUI HEADER ---
        header_frame = tk.Frame(self, bg=COLORS['bg_main'], pady=15)
        header_frame.pack(fill='x')
        tk.Label(header_frame, text="Správce aktualizací", font=("Segoe UI", 18, "bold"), bg=COLORS['bg_main'], fg=COLORS['fg']).pack(side="left", padx=20)

        # --- CONTROLS ---
        controls_frame = tk.Frame(self, bg=COLORS['bg_main'], padx=20)
        controls_frame.pack(fill='x', pady=(0, 10))

        self.stats_label = tk.Label(controls_frame, text="Klikněte na 'Obnovit' pro vyhledání aktualizací.", font=("Segoe UI", 10), bg=COLORS['bg_main'], fg=COLORS['sub_text'])
        self.stats_label.pack(side="left")

        btn_frame = tk.Frame(controls_frame, bg=COLORS['bg_main'])
        btn_frame.pack(side="right")

        self.refresh_btn = tk.Button(btn_frame, text="🔄 Obnovit", command=self.start_scan, bg=COLORS['input_bg'], fg="white", relief="flat", padx=15, pady=5, cursor="hand2")
        self.refresh_btn.pack(side="left", padx=5)
        
        self.update_all_btn = tk.Button(btn_frame, text="🚀 Aktualizovat vše", command=self.update_all, bg=COLORS['success'], fg="white", relief="flat", padx=15, pady=5, cursor="hand2", state="disabled")
        self.update_all_btn.pack(side="left", padx=5)

        self.progress = ttk.Progressbar(self, orient="horizontal", mode="indeterminate")
        self.progress.pack(fill='x', padx=20, pady=(0, 10))

        # --- LIST CONTAINER ---
        self.list_container = tk.Frame(self, bg=COLORS['bg_sidebar'])
        self.list_container.pack(fill='both', expand=True, padx=20, pady=(0, 20))
        
        self.list_canvas = tk.Canvas(self.list_container, bg=COLORS['bg_sidebar'], highlightthickness=0)
        self.list_scrollbar = ModernScrollbar(self.list_container, command=self.list_canvas.yview, bg=COLORS['bg_sidebar'])
        self.list_scrollable = tk.Frame(self.list_canvas, bg=COLORS['bg_sidebar'])
        
        self.list_scrollable.bind("<Configure>", lambda e: self.list_canvas.configure(scrollregion=self.list_canvas.bbox("all")))
        self.list_canvas.create_window((0, 0), window=self.list_scrollable, anchor="nw", width=480)
        self.list_canvas.configure(yscrollcommand=self.list_scrollbar.set)
        
        # Optimalizace změny velikosti
        self.list_canvas.bind("<Configure>", self._on_canvas_configure)

        self.list_canvas.pack(side="left", fill="both", expand=True)
        self.list_scrollbar.pack(side="right", fill="y")
        self._bind_mousewheel(self.list_container, self.list_canvas)

    def _on_canvas_configure(self, event):
        self.list_canvas.itemconfig(self.list_canvas.find_all()[0], width=event.width)

    def _bind_mousewheel(self, widget, canvas):
        def _on_mousewheel(event):
            if canvas.bbox("all"):
                scroll_height = canvas.bbox("all")[3]
                visible_height = canvas.winfo_height()
                if scroll_height <= visible_height: return 
            if event.num == 5 or event.delta < 0: canvas.yview_scroll(1, "units")
            elif event.num == 4 or event.delta > 0: canvas.yview_scroll(-1, "units")
        
        bind_enter = lambda e: {canvas.bind_all("<MouseWheel>", _on_mousewheel), canvas.bind_all("<Button-4>", _on_mousewheel), canvas.bind_all("<Button-5>", _on_mousewheel)}
        bind_leave = lambda e: {canvas.unbind_all("<MouseWheel>"), canvas.unbind_all("<Button-4>"), canvas.unbind_all("<Button-5>")}
        widget.bind('<Enter>', bind_enter)
        widget.bind('<Leave>', bind_leave)

    def start_scan(self):
        # Zastavíme předchozí vykreslování, pokud běží
        self.stop_rendering = True
        if self.rendering_task:
            self.after_cancel(self.rendering_task)
            
        self.progress.start(10)
        self.stats_label.config(text="Prohledávám nainstalované aplikace (čekejte)...")
        self.refresh_btn.config(state="disabled")
        self.update_all_btn.config(state="disabled")
        
        # Vyčistit seznam
        for widget in self.list_scrollable.winfo_children(): widget.destroy()
        self.list_canvas.yview_moveto(0)
        
        threading.Thread(target=self.scan_thread, daemon=True).start()

    def scan_thread(self):
        self.upgradable_apps = []
        installed_apps = []
        try:
            # Přidáno --source winget pro rychlost, odstraňte pokud chcete i MS Store
            cmd = "winget list --accept-source-agreements --source winget"
            
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            result = subprocess.run(cmd, capture_output=True, text=True, startupinfo=startupinfo, encoding='cp852', errors='replace')
            lines = result.stdout.splitlines()
            start_index = 0
            
            for i, line in enumerate(lines):
                if line.startswith("Name") and "Id" in line:
                    start_index = i + 2 
                    break
            
            for line in lines[start_index:]:
                parts = re.split(r'\s{2,}', line.strip())
                if len(parts) >= 3:
                    name = parts[0]
                    app_id = parts[1]
                    version = parts[2]
                    available = ""
                    if len(parts) >= 4:
                        potential = parts[3]
                        if potential and (potential[0].isdigit() or potential[0] == 'v'):
                            available = potential
                    
                    app_data = {"name": name, "id": app_id, "version": version, "available": available}
                    installed_apps.append(app_data)
                    if available: self.upgradable_apps.append(app_data)

            self.controller.after(0, self.display_apps, installed_apps)
        except Exception as e:
            print(f"Chyba scanu: {e}")
            self.controller.after(0, self.scan_error)

    def scan_error(self):
        self.progress.stop()
        self.stats_label.config(text="Chyba při načítání aplikací.")
        self.refresh_btn.config(state="normal")

    def display_apps(self, apps):
        self.progress.stop()
        self.refresh_btn.config(state="normal")
        self.stop_rendering = False # Povolíme vykreslování
        
        count_updatable = len(self.upgradable_apps)
        self.stats_label.config(text=f"Nainstalováno: {len(apps)} | Aktualizace: {count_updatable}")
        
        if count_updatable > 0:
            self.update_all_btn.config(state="normal", bg=COLORS['success'])
        else:
            self.update_all_btn.config(state="disabled", bg=COLORS['input_bg'])

        # Seřadíme: update první
        apps.sort(key=lambda x: (0 if x['available'] else 1, x['name'].lower()))
        
        # Spustíme generátor vykreslování
        self.render_generator = self._app_render_generator(apps)
        self._process_render_queue()

    def _app_render_generator(self, apps):
        """Generátor, který vrací aplikace jednu po druhé."""
        for app in apps:
            yield app

    def _process_render_queue(self):
        """Vykresluje dávky aplikací s vynuceným update_idletasks."""
        if self.stop_rendering: return

        # Vykreslíme malou dávku (např. 5 ks), aby GUI zůstalo responzivní
        # Menší dávka = plynulejší, ale celkově pomalejší načtení
        # Větší dávka = rychlejší načtení, ale možné záseky
        batch_size = 6 
        
        try:
            for _ in range(batch_size):
                if self.stop_rendering: return
                app = next(self.render_generator)
                self.create_app_card(app)
            
            # DŮLEŽITÉ: Vynutíme překreslení GUI po každé dávce, 
            # aby uživatel neviděl jen šedé pruhy, ale skutečný obsah.
            self.list_scrollable.update_idletasks()
            
            # Naplánujeme další dávku za 2ms
            self.rendering_task = self.after(2, self._process_render_queue)
            
        except StopIteration:
            # Hotovo
            self.list_canvas.update_idletasks()
            self.list_scrollbar.redraw()
            pass

    def _on_btn_hover(self, btn, color_enter, color_leave):
        btn.bind("<Enter>", lambda e: btn.config(bg=color_enter))
        btn.bind("<Leave>", lambda e: btn.config(bg=color_leave))

    def create_app_card(self, app):
        # KARTA (Visual Upgrade)
        card = tk.Frame(self.list_scrollable, bg=COLORS['item_bg'], pady=10, padx=15)
        # pack expand=False je důležité, aby se frame zbytečně neroztahoval, dokud nemá obsah
        card.pack(fill='x', padx=(10, 0), pady=4)

        # --- Levý kontejner (Ikonka + Text) ---
        left_container = tk.Frame(card, bg=COLORS['item_bg'])
        left_container.pack(side="left", fill="both", expand=True)

        # Ikonka (Fixní 48x48 box, aby text neposkakoval)
        icon_box = tk.Frame(left_container, bg=COLORS['item_bg'], width=48, height=48)
        icon_box.pack(side="left", padx=(0, 15), anchor="center")
        icon_box.pack_propagate(False) 

        icon_label = tk.Label(icon_box, image=self.default_icon, bg=COLORS['item_bg'])
        icon_label.pack(expand=True, fill="both")

        # Asynchronní načtení ikony
        try:
             threading.Thread(target=lambda: IconLoader.load_async(app, icon_label, self.controller), daemon=True).start()
        except: pass

        # Text
        text_box = tk.Frame(left_container, bg=COLORS['item_bg'])
        text_box.pack(side="left", fill="both", expand=True, anchor="w")

        # Název
        tk.Label(text_box, text=app['name'], font=("Segoe UI", 11, "bold"), 
                 bg=COLORS['item_bg'], fg="white", anchor="w").pack(fill="x")
        
        # ID a verze
        meta_info = f"ID: {app['id']}"
        tk.Label(text_box, text=meta_info, font=("Segoe UI", 8), 
                 bg=COLORS['item_bg'], fg=COLORS['sub_text'], anchor="w").pack(fill="x")
        
        ver_frame = tk.Frame(text_box, bg=COLORS['item_bg'])
        ver_frame.pack(fill="x", pady=(2,0))
        tk.Label(ver_frame, text="Verze: ", font=("Segoe UI", 8), bg=COLORS['item_bg'], fg="gray").pack(side="left")
        tk.Label(ver_frame, text=app['version'], font=("Segoe UI", 8), bg=COLORS['item_bg'], fg=COLORS['sub_text']).pack(side="left")

        # --- Pravý kontejner (Akce) ---
        right_container = tk.Frame(card, bg=COLORS['item_bg'])
        right_container.pack(side="right", anchor="center")

        if app['available']:
            # Nová verze + Tlačítko
            info_box = tk.Frame(right_container, bg=COLORS['item_bg'], padx=10)
            info_box.pack(side="left")
            
            tk.Label(info_box, text="Dostupná:", font=("Segoe UI", 8), bg=COLORS['item_bg'], fg="gray").pack(anchor="e")
            tk.Label(info_box, text=app['available'], font=("Segoe UI", 10, "bold"), bg=COLORS['item_bg'], fg=COLORS['accent']).pack(anchor="e")
            
            upd_btn = tk.Button(right_container, text="Aktualizovat", font=("Segoe UI", 9, "bold"), 
                                bg=COLORS['success'], fg="white", 
                                activebackground=COLORS['success_hover'], activeforeground="white",
                                relief="flat", padx=15, pady=5, cursor="hand2",
                                command=lambda a=app: self.update_single(a))
            upd_btn.pack(side="right")
            self._on_btn_hover(upd_btn, COLORS['success_hover'], COLORS['success'])
        else:
            # Aktuální
            status_box = tk.Frame(right_container, bg=COLORS['item_bg'], padx=10)
            status_box.pack(side="right")
            tk.Label(status_box, text="✓ Aktuální", font=("Segoe UI", 9), bg=COLORS['item_bg'], fg="#6c757d").pack()

    def update_single(self, app):
        if "installer" in self.controller.views:
            installer = self.controller.views["installer"]
            queue_item = {"name": app['name'], "id": app['id'], "version": app['available'], "website": "Unknown"}
            installer.add_item_to_queue(queue_item)
            messagebox.showinfo("Updater", f"{app['name']} byla přidána do instalační fronty.")

    def update_all(self):
        if not self.upgradable_apps: return
        if "installer" in self.controller.views:
            installer = self.controller.views["installer"]
            count = 0
            for app in self.upgradable_apps:
                queue_item = {"name": app['name'], "id": app['id'], "version": app['available'], "website": "Unknown"}
                installer.add_item_to_queue(queue_item)
                count += 1
            messagebox.showinfo("Updater", f"{count} aplikací bylo přidáno do instalační fronty.\nPřejděte na záložku Installer pro spuštění.")
            self.controller.switch_view("installer")
            
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
        try:
            model = genai.GenerativeModel('gemini-2.5-flash') 
            
            print(f"--- FÁZE 1: Zjišťování záměru pro: '{user_request}' ---")
            
            # ---------------------------------------------------------
            # 1. KROK: Zjištění záměru (Intent Recognition)
            # ---------------------------------------------------------
            intent_prompt = f"""
            Jsi expert na Windows software a Winget repozitář.
            Uživatel zadal: "{user_request}"

            Tvým úkolem je rozhodnout, jak tento dotaz hledat ve Winget.
            
            SCÉNÁŘ A (Konkrétní aplikace):
            Pokud uživatel myslí konkrétní program (i s překlepem, např. "discrd", "chrom", "vlc"),
            vráť POUZE opravený název.
            
            SCÉNÁŘ B (Obecný popis/Kategorie):
            Pokud uživatel hledá typ programu (např. "úprava videa", "webový prohlížeč", "pdf reader", "něco na hudbu"),
            vyber několik NEJLEPŠÍCH a NEJPOPULÁRNĚJŠÍCH aplikací pro Windows v této kategorii, které jsou určitě na Wingetu.
            
            Odpověz POUZE v tomto formátu (žádný markdown, žádný úvod):
            QUERIES: název1;název2;název3
            """

            search_terms = []
            try:
                intent_response = model.generate_content(intent_prompt)
                raw_intent = intent_response.text.strip()
                
                if "QUERIES:" in raw_intent:
                    clean_line = raw_intent.replace("QUERIES:", "").strip()
                    search_terms = [t.strip() for t in clean_line.split(";") if t.strip()]
                else:
                    search_terms = [user_request]
                    
                print(f"AI navrhlo hledat tyto výrazy: {search_terms}")

            except Exception as e:
                print(f"Chyba při zjišťování záměru: {e}")
                search_terms = [user_request]

            # ---------------------------------------------------------
            # 2. KROK: Hromadné hledání přes API (WINGET.RUN)
            # ---------------------------------------------------------
            
            # Nastavení progress baru (pokud existuje)
            if hasattr(self, 'progress'):
                self.progress['maximum'] = len(search_terms) * 100
            
            combined_results = []
            
            print(f"Hledám termíny přes API: {search_terms}")
            for term in search_terms:
                # Volání API
                try:
                    # Předpokládáme, že WingetRunAPI vrací seznam dictů [{'Name':..., 'Id':...}, ...]
                    api_results = WingetRunAPI.search(term, limit=5) 
                    if api_results:
                        combined_results.extend(api_results)
                except Exception as e:
                    print(f"Chyba při API hledání termínu '{term}': {e}")
                
                # Posun progress baru
                # if hasattr(self, 'current_prog'): self.current_prog += 100 

            # ---------------------------------------------------------
            # 3. KROK: Finální filtrace (s robustním Fallbackem)
            # ---------------------------------------------------------
            
            # Převedeme data pro AI
            combined_output_str = json.dumps(combined_results, indent=2, ensure_ascii=False)
            
            # Prompt (zkráceno pro přehlednost - použijte ten z předchozí odpovědi)
            filter_prompt = f"""
            Jsi striktní filtr. Uživatel hledal: "{user_request}"
            Surová data: {combined_output_str}
            
            INSTRUKCE:
            1. Najdi přesnou shodu. Pokud uživatel chce "Steam", ignoruj "Steam ROM Manager".
            2. Extrahuj name, id, version.
            3. Výstup pouze JSON pole.
            """

            try:
                # Pokusíme se zavolat AI
                response = model.generate_content(filter_prompt)
                raw_text = response.text
                json_str = raw_text.replace("```json", "").replace("```", "").strip()
                
                json_match = re.search(r'\[.*\]', json_str, re.DOTALL)
                data = []
                if json_match:
                    data = json.loads(json_match.group(0))
                
                for item in data:
                    if not item.get('version') or item['version'] == "Latest":
                        item['version'] = "Latest/Unknown"

                self.controller.after(0, self.display_search_results, data)

            except Exception as e:
                # Tady nastala ta chyba 429. Nyní spustíme BEZPEČNÝ Fallback.
                print(f"⚠️ AI nedostupné (Quota/Error): {e}")
                print("Spouštím záchranný režim (zobrazení surových dat)...")

                formatted_fallback = []
                seen_ids = set()

                for item in combined_results:
                    # 1. Bezpečné získání ID (zkoušíme různé varianty klíčů)
                    # WingetRun API vrací někdy 'id', někdy 'Id', někdy 'packageId'
                    p_id = item.get('id') or item.get('Id') or item.get('packageId')
                    
                    # 2. Bezpečné získání Názvu
                    p_name = item.get('name') or item.get('Name') or p_id or "Unknown"
                    
                    # 3. Bezpečné získání Verze
                    p_version = item.get('version') or item.get('Version') or "Latest"

                    # Pokud se nepovedlo najít ID, položku přeskočíme
                    if not p_id:
                        continue

                    # Deduplikace podle ID
                    if p_id in seen_ids:
                        continue
                    seen_ids.add(p_id)

                    formatted_fallback.append({
                        "name": p_name,
                        "id": p_id,
                        "version": p_version,
                        "website": "" 
                    })
                
                # Zobrazíme co máme, i když AI nefunguje
                self.controller.after(0, self.display_search_results, formatted_fallback)
                
        except Exception as glob_e:
            print(f"Kritická chyba ve vlákně: {glob_e}")
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